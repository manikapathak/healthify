"""
PDF blood report parser using pdfplumber.

Strategy:
  1. Extract all tables from the PDF (most lab reports have structured tables)
  2. If tables yield no parameters, fall back to raw text extraction
     and try to parse lines like "Hemoglobin    14.5    g/dL"
  3. Normalize parameter names using the same alias map as the CSV parser

pdfplumber handles scanned PDFs poorly — for those, use the image parser instead
(convert page to image and send to OpenAI Vision).
"""

import io
import re
from dataclasses import dataclass

import pdfplumber

from backend.core.parser import BloodParameter, ParseResult, normalize_name


class PDFParseError(Exception):
    pass


def parse_pdf(content: bytes) -> ParseResult:
    """
    Extract blood parameters from a PDF report.

    Tries table extraction first, then falls back to text line parsing.
    Returns the same ParseResult structure as parse_csv().
    """
    if not content:
        raise PDFParseError("PDF file is empty.")

    try:
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            if not pdf.pages:
                raise PDFParseError("PDF has no pages.")

            # Try table extraction across all pages
            result = _extract_from_tables(pdf)

            # Fall back to text parsing if tables gave nothing
            if not result.parameters and not result.unrecognized:
                result = _extract_from_text(pdf)

    except PDFParseError:
        raise
    except Exception as exc:
        raise PDFParseError(f"Could not read PDF: {exc}") from exc

    return result


# ---------------------------------------------------------------------------
# Table extraction
# ---------------------------------------------------------------------------

def _extract_from_tables(pdf: pdfplumber.PDF) -> ParseResult:
    parameters: list[BloodParameter] = []
    unrecognized: list[str] = []

    for page in pdf.pages:
        tables = page.extract_tables()
        for table in tables:
            p, u = _parse_table(table)
            parameters.extend(p)
            unrecognized.extend(u)

    return ParseResult(parameters=parameters, unrecognized=unrecognized)


def _parse_table(table: list[list[str | None]]) -> tuple[list[BloodParameter], list[str]]:
    if not table or len(table) < 2:
        return [], []

    # Detect column layout from header row
    headers = [str(c).strip().lower() if c else "" for c in table[0]]

    name_idx = _find_col_idx(headers, ["test", "parameter", "analyte", "investigation", "name", "test name"])
    value_idx = _find_col_idx(headers, ["value", "result", "observed", "your value", "patient value"])
    unit_idx = _find_col_idx(headers, ["unit", "units"])

    if name_idx is None or value_idx is None:
        # Try positional guess: col 0 = name, col 1 = value, col 2 = unit
        if len(headers) >= 2:
            name_idx, value_idx = 0, 1
            unit_idx = 2 if len(headers) > 2 else None
        else:
            return [], []

    parameters: list[BloodParameter] = []
    unrecognized: list[str] = []

    for row in table[1:]:  # skip header
        if not row or len(row) <= max(filter(None, [name_idx, value_idx])):
            continue

        raw_name = str(row[name_idx]).strip() if row[name_idx] else ""
        raw_value = str(row[value_idx]).strip() if row[value_idx] else ""
        unit = str(row[unit_idx]).strip() if unit_idx is not None and row[unit_idx] else ""

        if not raw_name or not raw_value:
            continue

        # Extract first numeric value (handles "14.5 (12-16)" → 14.5)
        numeric = _extract_numeric(raw_value)
        if numeric is None:
            unrecognized.append(raw_name)
            continue

        canonical = normalize_name(raw_name)
        if canonical is None:
            unrecognized.append(raw_name)
            continue

        parameters.append(BloodParameter(
            name=canonical,
            raw_name=raw_name,
            value=numeric,
            unit=unit,
        ))

    return parameters, unrecognized


# ---------------------------------------------------------------------------
# Text line extraction (fallback)
# ---------------------------------------------------------------------------

# Matches lines like:
#   Hemoglobin         14.5        g/dL
#   Glucose: 95 mg/dL
#   WBC    7,200   /uL
_LINE_PATTERN = re.compile(
    r"^([A-Za-z][A-Za-z0-9 _/\-\.]+?)"   # parameter name
    r"[\s:]+?"                              # separator
    r"(\d[\d,\.]*)"                         # numeric value
    r"\s*([A-Za-z/%µ][A-Za-z0-9/%µ·]*)?",  # optional unit
    re.MULTILINE,
)


def _extract_from_text(pdf: pdfplumber.PDF) -> ParseResult:
    all_text = "\n".join(
        page.extract_text() or ""
        for page in pdf.pages
    )

    parameters: list[BloodParameter] = []
    unrecognized: list[str] = []

    for match in _LINE_PATTERN.finditer(all_text):
        raw_name = match.group(1).strip()
        raw_value = match.group(2).replace(",", "")
        unit = (match.group(3) or "").strip()

        try:
            value = float(raw_value)
        except ValueError:
            unrecognized.append(raw_name)
            continue

        canonical = normalize_name(raw_name)
        if canonical is None:
            unrecognized.append(raw_name)
            continue

        # Avoid duplicates (same canonical name from multiple matches)
        if any(p.name == canonical for p in parameters):
            continue

        parameters.append(BloodParameter(
            name=canonical,
            raw_name=raw_name,
            value=value,
            unit=unit,
        ))

    return ParseResult(parameters=parameters, unrecognized=unrecognized)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _find_col_idx(headers: list[str], candidates: list[str]) -> int | None:
    for candidate in candidates:
        if candidate in headers:
            return headers.index(candidate)
    # Partial match fallback
    for candidate in candidates:
        for i, h in enumerate(headers):
            if candidate in h:
                return i
    return None


def _extract_numeric(text: str) -> float | None:
    """Extract first numeric value from a string like '14.5 (12.0-16.0) L'."""
    match = re.search(r"\d[\d,\.]*", text.strip())
    if match:
        try:
            return float(match.group().replace(",", ""))
        except ValueError:
            return None
    return None
