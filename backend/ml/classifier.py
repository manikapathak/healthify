"""
Logistic Regression classifier — Phase 5.

Loads a pre-trained multi-class classifier from models/classifier.joblib
and predicts condition probabilities from blood parameters.

Usage:
    from backend.ml.classifier import predict, ClassifierResult

    result = predict(params)
    print(result.top_condition, result.top_probability)
"""

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import joblib
import numpy as np

from backend.core.parser import BloodParameter

_MODEL_FILE = Path(__file__).parent.parent.parent / "models" / "classifier.joblib"

# Human-readable names for canonical condition identifiers
_DISPLAY_NAMES: dict[str, str] = {
    "healthy":                         "Healthy",
    "iron_deficiency_anemia":          "Iron Deficiency Anemia",
    "normocytic_hypochromic_anemia":   "Normocytic Hypochromic Anemia",
    "normocytic_normochromic_anemia":  "Normocytic Normochromic Anemia",
    "microcytic_anemia":               "Microcytic Anemia",
    "macrocytic_anemia":               "Macrocytic Anemia",
    "thrombocytopenia":                "Thrombocytopenia",
    "leukemia":                        "Leukemia",
    "type_2_diabetes":                 "Type 2 Diabetes",
    "chronic_kidney_disease":          "Chronic Kidney Disease",
    "liver_disease":                   "Liver Disease",
    "hypothyroidism":                  "Hypothyroidism",
    "heart_disease":                   "Heart Disease",
}


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ClassifierModelData:
    model: object
    scaler: object
    feature_names: list[str]
    classes: list[str]
    midpoints: dict[str, float]


@dataclass(frozen=True)
class ConditionProbability:
    condition: str
    display_name: str
    probability: float


@dataclass(frozen=True)
class ClassifierResult:
    top_condition: str
    top_probability: float
    probabilities: list[ConditionProbability]   # sorted descending by probability


# ---------------------------------------------------------------------------
# Model loading (cached)
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def load_classifier() -> ClassifierModelData:
    """Load the trained classifier artifact. Cached after first call."""
    data = joblib.load(_MODEL_FILE)
    return ClassifierModelData(
        model=data["model"],
        scaler=data["scaler"],
        feature_names=data["feature_names"],
        classes=data["classes"],
        midpoints=data["midpoints"],
    )


# ---------------------------------------------------------------------------
# Feature vector construction
# ---------------------------------------------------------------------------

def build_feature_vector(
    params: list[BloodParameter],
    feature_names: list[str],
    midpoints: dict[str, float],
) -> np.ndarray:
    """
    Map BloodParameter objects onto a fixed-length feature vector.
    Missing parameters are filled with training-set column medians.
    """
    param_map = {p.name: p.value for p in params}
    vec = np.array(
        [param_map.get(name, midpoints.get(name, 0.0)) for name in feature_names],
        dtype=float,
    )
    return vec


# ---------------------------------------------------------------------------
# Prediction
# ---------------------------------------------------------------------------

def predict(params: list[BloodParameter]) -> ClassifierResult:
    """
    Predict condition probabilities from blood parameters.

    Returns a ClassifierResult with all class probabilities sorted
    descending, plus the top condition and its probability.
    """
    model_data = load_classifier()

    vec = build_feature_vector(params, model_data.feature_names, model_data.midpoints)
    vec_scaled = model_data.scaler.transform(vec.reshape(1, -1))

    proba = model_data.model.predict_proba(vec_scaled)[0]

    condition_probs = sorted(
        [
            ConditionProbability(
                condition=cls,
                display_name=_DISPLAY_NAMES.get(cls, cls.replace("_", " ").title()),
                probability=round(float(p), 4),
            )
            for cls, p in zip(model_data.classes, proba)
        ],
        key=lambda cp: cp.probability,
        reverse=True,
    )

    return ClassifierResult(
        top_condition=condition_probs[0].condition,
        top_probability=condition_probs[0].probability,
        probabilities=condition_probs,
    )
