"""
Train Logistic Regression Classifier — Phase 5

Reads data/classifier_training_data.csv, trains a multi-class
LogisticRegression with StratifiedKFold cross-validation, and saves
the artifact to models/classifier.joblib.

Usage:
    python scripts/train_classifier.py

Output:
    models/classifier.joblib  — {model, scaler, feature_names, classes, midpoints}
"""

from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).parent.parent
TRAINING_FILE = ROOT / "data" / "classifier_training_data.csv"
OUTPUT_FILE = ROOT / "models" / "classifier.joblib"

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

# Drop features with fewer than this many non-null values across the dataset
MIN_COVERAGE = 50

RANDOM_STATE = 42


def load_data() -> pd.DataFrame:
    df = pd.read_csv(TRAINING_FILE)
    print(f"Loaded: {len(df)} rows, {df[LABEL_COL].nunique()} classes")
    return df


def select_features(df: pd.DataFrame) -> list[str]:
    available = [c for c in FEATURE_COLS if c in df.columns]
    coverage = df[available].notna().sum()
    selected = [c for c in available if coverage[c] >= MIN_COVERAGE]
    print(f"\nFeatures selected: {len(selected)}/{len(available)}")
    return selected


def compute_midpoints(df: pd.DataFrame, features: list[str]) -> dict[str, float]:
    return {
        col: float(df[col].dropna().median()) if df[col].notna().any() else 0.0
        for col in features
    }


def prepare_matrix(
    df: pd.DataFrame,
    features: list[str],
    midpoints: dict[str, float],
) -> tuple[np.ndarray, np.ndarray]:
    X = df[features].copy()
    for col in features:
        X[col] = X[col].fillna(midpoints[col])
    return X.values.astype(float), df[LABEL_COL].values


def train(
    X: np.ndarray,
    y: np.ndarray,
) -> tuple[StandardScaler, LogisticRegression]:
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    clf = LogisticRegression(
        C=1.0,
        class_weight="balanced",
        max_iter=1000,
        random_state=RANDOM_STATE,
        solver="lbfgs",
    )

    # 5-fold stratified cross-validation
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)
    cv_scores = cross_val_score(clf, X_scaled, y, cv=cv, scoring="f1_weighted")
    print(f"\nCross-validation F1 (weighted): {cv_scores.mean():.3f} ± {cv_scores.std():.3f}")

    # Train on full dataset
    clf.fit(X_scaled, y)

    # Per-class report on training data (for reference)
    y_pred = clf.predict(X_scaled)
    print("\nClassification report (training data):")
    print(classification_report(y, y_pred, zero_division=0))

    return scaler, clf


def save(
    scaler: StandardScaler,
    clf: LogisticRegression,
    feature_names: list[str],
    midpoints: dict[str, float],
) -> None:
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    artifact = {
        "model": clf,
        "scaler": scaler,
        "feature_names": feature_names,
        "classes": clf.classes_.tolist(),
        "midpoints": midpoints,
    }
    joblib.dump(artifact, OUTPUT_FILE)
    print(f"\nSaved: {OUTPUT_FILE}")
    print(f"Classes: {clf.classes_.tolist()}")


if __name__ == "__main__":
    print("Training Logistic Regression classifier...\n")
    df = load_data()
    features = select_features(df)
    midpoints = compute_midpoints(df, features)
    X, y = prepare_matrix(df, features, midpoints)
    scaler, clf = train(X, y)
    save(scaler, clf, features, midpoints)
    print("\nDone.")
