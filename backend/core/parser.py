"""
CSV parser for blood reports.

Handles common formats:
  - Single-row: one column per parameter
  - Multi-row: each row is one parameter (name, value, unit)

All parameter names are normalized to a canonical key (e.g. "Hb" → "hemoglobin").
"""

import io
from dataclasses import dataclass

import pandas as pd

# Canonical name → list of aliases (case-insensitive)
_ALIASES: dict[str, list[str]] = {
    "hemoglobin":       ["hemoglobin", "hb", "hgb", "haemoglobin"],
    "rbc":              ["rbc", "red blood cells", "red blood cell count", "erythrocytes"],
    "wbc":              ["wbc", "white blood cells", "white blood cell count", "leukocytes", "tbc"],
    "platelets":        ["platelets", "plt", "platelet count", "thrombocytes"],
    "hematocrit":       ["hematocrit", "hct", "packed cell volume", "pcv"],
    "mcv":              ["mcv", "mean corpuscular volume"],
    "mch":              ["mch", "mean corpuscular hemoglobin"],
    "mchc":             ["mchc", "mean corpuscular hemoglobin concentration"],
    "glucose":          ["glucose", "blood glucose", "fasting glucose", "fbs", "rbs"],
    "hba1c":            ["hba1c", "hb a1c", "glycated hemoglobin", "glycohemoglobin", "a1c"],
    "cholesterol":      ["cholesterol", "total cholesterol", "tc"],
    "ldl":              ["ldl", "ldl cholesterol", "low density lipoprotein", "ldl-c"],
    "hdl":              ["hdl", "hdl cholesterol", "high density lipoprotein", "hdl-c"],
    "triglycerides":    ["triglycerides", "tg", "trigs"],
    "creatinine":       ["creatinine", "serum creatinine", "cr"],
    "bun":              ["bun", "blood urea nitrogen", "urea nitrogen", "urea"],
    "uric_acid":        ["uric acid", "ua", "serum uric acid"],
    "alt":              ["alt", "alanine aminotransferase", "sgpt"],
    "ast":              ["ast", "aspartate aminotransferase", "sgot"],
    "alp":              ["alp", "alkaline phosphatase"],
    "bilirubin_total":  ["bilirubin total", "total bilirubin", "tbil"],
    "bilirubin_direct": ["bilirubin direct", "direct bilirubin", "dbil"],
    "albumin":          ["albumin", "serum albumin"],
    "protein_total":    ["total protein", "protein total", "tp"],
    "tsh":              ["tsh", "thyroid stimulating hormone"],
    "t3":               ["t3", "triiodothyronine"],
    "t4":               ["t4", "thyroxine"],
    "ferritin":         ["ferritin", "serum ferritin"],
    "iron":             ["iron", "serum iron", "fe"],
    "tibc":             ["tibc", "total iron binding capacity"],
    "vitamin_b12":      ["vitamin b12", "b12", "cobalamin", "vit b12"],
    "vitamin_d":        ["vitamin d", "25-oh vitamin d", "25-hydroxyvitamin d", "vit d", "25ohd"],
    "sodium":           ["sodium", "na", "serum sodium"],
    "potassium":        ["potassium", "k", "serum potassium"],
    "calcium":          ["calcium", "ca", "serum calcium"],
    "phosphorus":       ["phosphorus", "phosphate", "po4"],
    "magnesium":        ["magnesium", "mg", "serum magnesium"],
    "chloride":         ["chloride", "cl"],
    "bicarbonate":      ["bicarbonate", "hco3", "co2"],
}

# Build reverse lookup: alias → canonical
_ALIAS_MAP: dict[str, str] = {
    alias: canonical
    for canonical, aliases in _ALIASES.items()
    for alias in aliases
}


@dataclass(frozen=True)
class BloodParameter:
    name: str        # canonical name
    raw_name: str    # original name from file
    value: float
    unit: str


@dataclass(frozen=True)
class ParseResult:
    parameters: list[BloodParameter]
    unrecognized: list[str]   # raw names we couldn't normalize


class ParseError(Exception):
    pass


def normalize_name(raw: str) -> str | None:
    """Return canonical parameter name or None if unrecognized."""
    key = raw.strip().lower()
    return _ALIAS_MAP.get(key)


def parse_csv(content: bytes) -> ParseResult:
    """
    Parse a blood report CSV.

    Tries two layouts:
      1. Multi-row: columns contain 'parameter'/'test'/'name', 'value'/'result', 'unit'
      2. Single-row: first row is headers (parameter names), second row is values
    """
    try:
        df = pd.read_csv(io.BytesIO(content))
    except Exception as exc:
        raise ParseError(f"Could not read CSV: {exc}") from exc

    if df.empty:
        raise ParseError("CSV file is empty.")

    cols_lower = [c.strip().lower() for c in df.columns]

    # --- Multi-row layout ---
    name_col = _find_col(cols_lower, ["parameter", "test", "test name", "name", "analyte"])
    value_col = _find_col(cols_lower, ["value", "result", "observed value", "your value"])
    unit_col = _find_col(cols_lower, ["unit", "units", "reference unit"])

    if name_col is not None and value_col is not None:
        return _parse_multirow(df, df.columns[name_col], df.columns[value_col],
                               df.columns[unit_col] if unit_col is not None else None)

    # --- Single-row layout ---
    return _parse_singlerow(df)


def _find_col(cols_lower: list[str], candidates: list[str]) -> int | None:
    for candidate in candidates:
        if candidate in cols_lower:
            return cols_lower.index(candidate)
    return None


def _parse_multirow(df: pd.DataFrame, name_col: str, value_col: str,
                    unit_col: str | None) -> ParseResult:
    parameters: list[BloodParameter] = []
    unrecognized: list[str] = []

    for _, row in df.iterrows():
        raw_name = str(row[name_col]).strip()
        raw_value = row[value_col]

        try:
            value = float(str(raw_value).replace(",", "").strip())
        except ValueError:
            unrecognized.append(raw_name)
            continue

        unit = str(row[unit_col]).strip() if unit_col and pd.notna(row[unit_col]) else ""
        canonical = normalize_name(raw_name)

        if canonical is None:
            unrecognized.append(raw_name)
            continue

        parameters.append(BloodParameter(
            name=canonical,
            raw_name=raw_name,
            value=value,
            unit=unit,
        ))

    return ParseResult(parameters=parameters, unrecognized=unrecognized)


def _parse_singlerow(df: pd.DataFrame) -> ParseResult:
    """Headers are parameter names, first data row is values."""
    if len(df) < 1:
        raise ParseError("CSV has headers but no data rows.")

    row = df.iloc[0]
    parameters: list[BloodParameter] = []
    unrecognized: list[str] = []

    for col in df.columns:
        raw_name = str(col).strip()
        try:
            value = float(str(row[col]).replace(",", "").strip())
        except ValueError:
            unrecognized.append(raw_name)
            continue

        canonical = normalize_name(raw_name)
        if canonical is None:
            unrecognized.append(raw_name)
            continue

        parameters.append(BloodParameter(
            name=canonical,
            raw_name=raw_name,
            value=value,
            unit="",
        ))

    return ParseResult(parameters=parameters, unrecognized=unrecognized)
