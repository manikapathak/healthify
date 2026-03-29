"""
Classifier Training Data Preparation — Phase 5

Loads 5 labeled Kaggle datasets, maps columns to canonical parameter names
and labels to canonical condition names, merges into a single
data/classifier_training_data.csv.

Usage:
    python scripts/prepare_classifier_data.py

Output:
    data/classifier_training_data.csv  — canonical features + label column
"""

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).parent.parent
KAGGLE_DIR = ROOT / "data" / "kaggle"
OUTPUT_FILE = ROOT / "data" / "classifier_training_data.csv"

# Blood parameter feature columns (same canonical names as Phase 3)
FEATURE_COLS = [
    "hemoglobin", "rbc", "wbc", "platelets", "hematocrit",
    "mcv", "mch", "mchc",
    "glucose", "hba1c",
    "creatinine", "bun",
    "alt", "ast", "alp", "bilirubin_total", "albumin",
    "tsh", "t3", "t4",
    "cholesterol",
]

LABEL_COL = "label"


# ---------------------------------------------------------------------------
# Per-dataset loaders — each returns (features_df, labels_series)
# ---------------------------------------------------------------------------

def load_cbc(path: Path):
    """diagnosed_cbc_data_v4.csv — 1281 rows, 9 conditions."""
    df = pd.read_csv(path)
    label_map = {
        "Healthy":                          "healthy",
        "Iron deficiency anemia":           "iron_deficiency_anemia",
        "Normocytic hypochromic anemia":    "normocytic_hypochromic_anemia",
        "Normocytic normochromic anemia":   "normocytic_normochromic_anemia",
        "Other microcytic anemia":          "microcytic_anemia",
        "Macrocytic anemia":                "macrocytic_anemia",
        "Thrombocytopenia":                 "thrombocytopenia",
        "Leukemia":                         "leukemia",
        "Leukemia with thrombocytopenia":   "leukemia",  # merge with leukemia
    }
    features = pd.DataFrame({
        "hemoglobin": pd.to_numeric(df["HGB"],  errors="coerce"),
        "hematocrit": pd.to_numeric(df["HCT"],  errors="coerce"),
        "rbc":        pd.to_numeric(df["RBC"],  errors="coerce"),
        "wbc":        pd.to_numeric(df["WBC"],  errors="coerce") * 1000,
        "platelets":  pd.to_numeric(df["PLT"],  errors="coerce") * 1000,
        "mcv":        pd.to_numeric(df["MCV"],  errors="coerce"),
        "mch":        pd.to_numeric(df["MCH"],  errors="coerce"),
        "mchc":       pd.to_numeric(df["MCHC"], errors="coerce"),
    })
    labels = df["Diagnosis"].map(label_map)
    return features, labels


def load_diabetes(path: Path):
    """diabetes.csv — 768 rows, glucose only."""
    df = pd.read_csv(path)
    glucose = pd.to_numeric(df["Glucose"], errors="coerce").replace(0, np.nan)
    features = pd.DataFrame({"glucose": glucose})
    labels = df["Outcome"].map({1: "type_2_diabetes", 0: "healthy"})
    return features, labels


def load_kidney(path: Path):
    """kidney_disease.csv — 400 rows, metabolic panel."""
    df = pd.read_csv(path)
    # Strip whitespace from classification column (contains 'ckd\t')
    df["classification"] = df["classification"].str.strip()
    features = pd.DataFrame({
        "glucose":    pd.to_numeric(df["bgr"],  errors="coerce"),
        "bun":        pd.to_numeric(df["bu"],   errors="coerce"),
        "creatinine": pd.to_numeric(df["sc"],   errors="coerce"),
        "hemoglobin": pd.to_numeric(df["hemo"], errors="coerce"),
        "wbc":        pd.to_numeric(df["wc"],   errors="coerce"),
        "rbc":        pd.to_numeric(df["rc"],   errors="coerce"),
    })
    labels = df["classification"].map({"ckd": "chronic_kidney_disease", "notckd": "healthy"})
    return features, labels


def load_liver(path: Path):
    """indian_liver_patient.csv — 583 rows, liver panel."""
    df = pd.read_csv(path)
    features = pd.DataFrame({
        "bilirubin_total": pd.to_numeric(df["Total_Bilirubin"],           errors="coerce"),
        "alt":             pd.to_numeric(df["Alamine_Aminotransferase"],   errors="coerce"),
        "ast":             pd.to_numeric(df["Aspartate_Aminotransferase"], errors="coerce"),
        "alp":             pd.to_numeric(df["Alkaline_Phosphotase"],       errors="coerce"),
        "albumin":         pd.to_numeric(df["Albumin"],                    errors="coerce"),
    })
    # Dataset=1 → disease, Dataset=2 → healthy
    labels = df["Dataset"].map({1: "liver_disease", 2: "healthy"})
    return features, labels


def load_thyroid(path: Path):
    """cleaned_dataset_Thyroid1.csv — 3771 rows, thyroid panel."""
    df = pd.read_csv(path)
    df = df.replace("?", np.nan)
    features = pd.DataFrame({
        "tsh": pd.to_numeric(df.get("TSH",  pd.Series(dtype=float)), errors="coerce"),
        "t3":  pd.to_numeric(df.get("T3",   pd.Series(dtype=float)), errors="coerce"),
        "t4":  pd.to_numeric(df.get("TT4",  pd.Series(dtype=float)), errors="coerce"),
    })
    labels = df["binaryClass"].map({1: "hypothyroidism", 0: "healthy"})
    return features, labels


LOADERS = {
    "diagnosed_cbc_data_v4.csv":    load_cbc,
    "diabetes.csv":                 load_diabetes,
    "kidney_disease.csv":           load_kidney,
    "indian_liver_patient.csv":     load_liver,
    "cleaned_dataset_Thyroid1.csv": load_thyroid,
}

# Physical limits — same as Phase 3 to keep data clean
LIMITS = {
    "hemoglobin": (0, 25), "rbc": (0, 10), "wbc": (0, 500_000),
    "platelets": (0, 2_000_000), "hematocrit": (0, 100),
    "mcv": (0, 200), "mch": (0, 60), "mchc": (0, 50),
    "glucose": (0, 1000), "hba1c": (0, 20),
    "creatinine": (0, 50), "bun": (0, 300),
    "alt": (0, 10000), "ast": (0, 10000), "alp": (0, 5000),
    "bilirubin_total": (0, 50), "albumin": (0, 10),
    "tsh": (0, 200), "t3": (0, 1000), "t4": (0, 30),
}


def prepare() -> pd.DataFrame:
    frames = []
    for filename, loader in LOADERS.items():
        path = KAGGLE_DIR / filename
        if not path.exists():
            print(f"  SKIP (not found): {filename}")
            continue
        try:
            features, labels = loader(path)
            # Drop rows with unmapped labels
            valid = labels.notna()
            features = features[valid].reset_index(drop=True)
            labels = labels[valid].reset_index(drop=True)
            # Reindex to full feature set, missing columns → NaN
            features = features.reindex(columns=FEATURE_COLS)
            features[LABEL_COL] = labels.values
            frames.append(features)
            print(f"  OK  {filename:45s} {len(features):5d} rows, "
                  f"{features[FEATURE_COLS].notna().any().sum()} features, "
                  f"{labels.nunique()} classes")
        except Exception as exc:
            print(f"  ERR {filename}: {exc}")

    merged = pd.concat(frames, ignore_index=True)

    # Apply physical limits
    for col, (lo, hi) in LIMITS.items():
        if col in merged.columns:
            merged[col] = merged[col].where(
                merged[col].between(lo, hi, inclusive="both"), other=np.nan
            )

    # Drop rows where ALL feature values are NaN
    feature_only = merged[FEATURE_COLS]
    merged = merged[feature_only.notna().any(axis=1)].reset_index(drop=True)

    print(f"\nFinal dataset: {len(merged)} rows")
    print(f"Class distribution:")
    for label, count in merged[LABEL_COL].value_counts().items():
        print(f"  {label:45s} {count:5d} rows")

    return merged


def save(df: pd.DataFrame) -> None:
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_FILE, index=False)
    print(f"\nSaved: {OUTPUT_FILE}")


if __name__ == "__main__":
    print("Preparing classifier training data...\n")
    df = prepare()
    save(df)
    print("\nDone.")
