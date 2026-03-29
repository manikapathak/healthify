"""
Training Data Preparation — Phase 3 (Isolation Forest)

Merges all 8 Kaggle datasets into a single training_data.csv with
canonical blood parameter column names. No labels — IF is unsupervised.

Usage:
    python scripts/prepare_training_data.py

Output:
    data/training_data.csv   — merged, canonical columns, no normalization yet
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).parent.parent
KAGGLE_DIR = ROOT / "data" / "kaggle"
OUTPUT_FILE = ROOT / "data" / "training_data.csv"
REF_FILE = ROOT / "data" / "reference_ranges.json"

# All canonical parameter names we care about (must exist in reference_ranges.json)
CANONICAL_PARAMS = [
    "hemoglobin", "rbc", "wbc", "platelets", "hematocrit",
    "mcv", "mch", "mchc", "glucose", "hba1c",
    "cholesterol", "ldl", "hdl", "triglycerides",
    "creatinine", "bun", "uric_acid",
    "alt", "ast", "alp", "bilirubin_total", "bilirubin_direct",
    "albumin", "protein_total",
    "tsh", "t3", "t4",
    "ferritin", "iron", "tibc",
    "vitamin_b12", "vitamin_d",
    "sodium", "potassium", "calcium",
]


# ---------------------------------------------------------------------------
# Per-dataset loaders
# Each returns a DataFrame with only canonical column names
# ---------------------------------------------------------------------------

def load_diagnosed_cbc(path: Path) -> pd.DataFrame:
    """diagnosed_cbc_data_v4.csv — 1281 rows, best CBC coverage.
    WBC and PLT are in K/uL — multiply by 1000 to normalise to /uL."""
    df = pd.read_csv(path)
    return pd.DataFrame({
        "hemoglobin": pd.to_numeric(df["HGB"],  errors="coerce"),
        "hematocrit": pd.to_numeric(df["HCT"],  errors="coerce"),
        "rbc":        pd.to_numeric(df["RBC"],  errors="coerce"),
        "wbc":        pd.to_numeric(df["WBC"],  errors="coerce") * 1000,
        "platelets":  pd.to_numeric(df["PLT"],  errors="coerce") * 1000,
        "mcv":        pd.to_numeric(df["MCV"],  errors="coerce"),
        "mch":        pd.to_numeric(df["MCH"],  errors="coerce"),
        "mchc":       pd.to_numeric(df["MCHC"], errors="coerce"),
    })


def load_blood_count(path: Path) -> pd.DataFrame:
    """blood_count_dataset.csv — 417 rows, unlabeled CBC"""
    df = pd.read_csv(path)
    return pd.DataFrame({
        "hemoglobin": pd.to_numeric(df["Hemoglobin"], errors="coerce"),
        "platelets":  pd.to_numeric(df["Platelet_Count"], errors="coerce"),
        "wbc":        pd.to_numeric(df["White_Blood_Cells"], errors="coerce"),
        "rbc":        pd.to_numeric(df["Red_Blood_Cells"], errors="coerce"),
        "mcv":        pd.to_numeric(df["MCV"], errors="coerce"),
        "mch":        pd.to_numeric(df["MCH"], errors="coerce"),
        "mchc":       pd.to_numeric(df["MCHC"], errors="coerce"),
    })


def load_diabetes(path: Path) -> pd.DataFrame:
    """diabetes.csv — 767 rows, glucose only usable"""
    df = pd.read_csv(path)
    # Glucose=0 in this dataset means missing — replace with NaN
    glucose = pd.to_numeric(df["Glucose"], errors="coerce").replace(0, np.nan)
    return pd.DataFrame({"glucose": glucose})


def load_kidney(path: Path) -> pd.DataFrame:
    """kidney_disease.csv — 400 rows, metabolic panel"""
    df = pd.read_csv(path)
    return pd.DataFrame({
        "glucose":    pd.to_numeric(df["bgr"],  errors="coerce"),
        "bun":        pd.to_numeric(df["bu"],   errors="coerce"),
        "creatinine": pd.to_numeric(df["sc"],   errors="coerce"),
        "sodium":     pd.to_numeric(df["sod"],  errors="coerce"),
        "potassium":  pd.to_numeric(df["pot"],  errors="coerce"),
        "hemoglobin": pd.to_numeric(df["hemo"], errors="coerce"),
        "wbc":        pd.to_numeric(df["wc"],   errors="coerce"),
        "rbc":        pd.to_numeric(df["rc"],   errors="coerce"),
    })


def load_liver(path: Path) -> pd.DataFrame:
    """indian_liver_patient.csv — 583 rows, liver panel"""
    df = pd.read_csv(path)
    return pd.DataFrame({
        "bilirubin_total":  pd.to_numeric(df["Total_Bilirubin"],           errors="coerce"),
        "bilirubin_direct": pd.to_numeric(df["Direct_Bilirubin"],          errors="coerce"),
        "alp":              pd.to_numeric(df["Alkaline_Phosphotase"],       errors="coerce"),
        "alt":              pd.to_numeric(df["Alamine_Aminotransferase"],   errors="coerce"),
        "ast":              pd.to_numeric(df["Aspartate_Aminotransferase"], errors="coerce"),
        "protein_total":    pd.to_numeric(df["Total_Protiens"],             errors="coerce"),
        "albumin":          pd.to_numeric(df["Albumin"],                    errors="coerce"),
    })


def load_thyroid(path: Path) -> pd.DataFrame:
    """cleaned_dataset_Thyroid1.csv or hypothyroid.csv — thyroid panel"""
    df = pd.read_csv(path)
    # Replace '?' with NaN
    df = df.replace("?", np.nan)
    result = pd.DataFrame({
        "tsh": pd.to_numeric(df.get("TSH", pd.Series(dtype=float)), errors="coerce"),
        "t3":  pd.to_numeric(df.get("T3",  pd.Series(dtype=float)), errors="coerce"),
        "t4":  pd.to_numeric(df.get("TT4", pd.Series(dtype=float)), errors="coerce"),
    })
    return result


def load_heart(path: Path) -> pd.DataFrame:
    """heart.csv — 918 rows, cholesterol only"""
    df = pd.read_csv(path)
    # Cholesterol=0 means missing in this dataset
    chol = pd.to_numeric(df["Cholesterol"], errors="coerce").replace(0, np.nan)
    return pd.DataFrame({"cholesterol": chol})


def load_cbc_excel(path: Path) -> pd.DataFrame:
    """cbc information.xlsx — 500 rows, full CBC panel.
    WBC and PLT are in K/uL — multiply by 1000 to normalise to /uL."""
    df = pd.read_excel(path)
    return pd.DataFrame({
        "wbc":        pd.to_numeric(df["WBC"],  errors="coerce") * 1000,
        "rbc":        pd.to_numeric(df["RBC"],  errors="coerce"),
        "hemoglobin": pd.to_numeric(df["HGB"],  errors="coerce"),
        "hematocrit": pd.to_numeric(df["HCT"],  errors="coerce"),
        "mcv":        pd.to_numeric(df["MCV"],  errors="coerce"),
        "mch":        pd.to_numeric(df["MCH"],  errors="coerce"),
        "mchc":       pd.to_numeric(df["MCHC"], errors="coerce"),
        "platelets":  pd.to_numeric(df["PLT"],  errors="coerce") * 1000,
    })


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

LOADERS = {
    "diagnosed_cbc_data_v4.csv":  load_diagnosed_cbc,
    "blood_count_dataset.csv":    load_blood_count,
    "diabetes.csv":               load_diabetes,
    "kidney_disease.csv":         load_kidney,
    "indian_liver_patient.csv":   load_liver,
    "cleaned_dataset_Thyroid1.csv": load_thyroid,
    "hypothyroid.csv":            load_thyroid,
    "heart.csv":                  load_heart,
    "cbc information.xlsx":       load_cbc_excel,
}


def prepare() -> pd.DataFrame:
    frames = []
    for filename, loader in LOADERS.items():
        path = KAGGLE_DIR / filename
        if not path.exists():
            print(f"  SKIP (not found): {filename}")
            continue
        try:
            df = loader(path)
            # Reindex to full canonical column set, filling missing cols with NaN
            df = df.reindex(columns=CANONICAL_PARAMS)
            frames.append(df)
            print(f"  OK  {filename:45s} {len(df):5d} rows, "
                  f"{df.notna().any().sum()} params with data")
        except Exception as exc:
            print(f"  ERR {filename}: {exc}")

    merged = pd.concat(frames, ignore_index=True)

    # Drop rows where ALL values are NaN
    merged = merged.dropna(how="all")

    # Remove physically impossible values using hard limits
    limits = {
        "hemoglobin": (0, 25), "rbc": (0, 10), "wbc": (0, 500_000),
        "platelets": (0, 2_000_000), "hematocrit": (0, 100),
        "mcv": (0, 200), "mch": (0, 60), "mchc": (0, 50),
        "glucose": (0, 1000), "hba1c": (0, 20),
        "cholesterol": (0, 1000), "ldl": (0, 800), "hdl": (0, 200),
        "triglycerides": (0, 5000), "creatinine": (0, 50),
        "bun": (0, 300), "alt": (0, 10000), "ast": (0, 10000),
        "alp": (0, 5000), "bilirubin_total": (0, 50),
        "albumin": (0, 10), "protein_total": (0, 20),
        "tsh": (0, 200), "t3": (0, 1000), "t4": (0, 30),
        "ferritin": (0, 10000), "iron": (0, 500),
        "sodium": (80, 180), "potassium": (1, 12), "calcium": (0, 20),
    }
    for col, (lo, hi) in limits.items():
        if col in merged.columns:
            merged[col] = merged[col].where(
                merged[col].between(lo, hi, inclusive="both"), other=np.nan
            )

    print(f"\nFinal dataset: {len(merged)} rows x {len(merged.columns)} params")
    print(f"Parameter coverage (non-null rows per param):")
    coverage = merged.notna().sum().sort_values(ascending=False)
    for param_name, count in coverage.items():
        if count > 0:
            print(f"  {param_name:25s} {count:5d} rows")

    return merged


def save(df: pd.DataFrame) -> None:
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_FILE, index=False)
    print(f"\nSaved: {OUTPUT_FILE}")


if __name__ == "__main__":
    print("Preparing training data from all Kaggle datasets...\n")
    df = prepare()
    save(df)
    print("\nDone.")
