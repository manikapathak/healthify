"""
XGBoost classifier with SMOTE + calibrated probabilities.

Loads a pre-trained multi-class classifier from models/classifier.joblib
and predicts condition probabilities from blood parameters.

The artifact stores integer-encoded class labels mapped back to string
condition names via the 'classes' list (index = integer label).

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

_HEALTHY_DEFAULTS: dict[str, float] = {
    "hemoglobin":           14.0,
    "rbc":                   4.8,
    "wbc":                6500.0,
    "platelets":         250000.0,
    "hematocrit":           42.0,
    "mcv":                  90.0,
    "mch":                  30.0,
    "mchc":                 34.0,
    "glucose":              85.0,
    "hba1c":                 5.2,
    "creatinine":            0.9,
    "bun":                  14.0,
    "alt":                  22.0,
    "ast":                  22.0,
    "alp":                  70.0,
    "bilirubin_total":       0.7,
    "albumin":               4.2,
    "tsh":                   2.0,
    "t3":                    1.2,
    "t4":                    8.0,
    "cholesterol":         180.0,
    # Derived ratio features — healthy midpoints
    "bun_creatinine_ratio":  14.0 / 0.9,   # ~15.6
    "ast_alt_ratio":         22.0 / 22.0,  # 1.0
    "mch_mcv_ratio":         30.0 / 90.0,  # 0.33
    "hemoglobin_rbc_ratio":  14.0 / 4.8,   # ~2.92
}


def build_feature_vector(
    params: list[BloodParameter],
    feature_names: list[str],
    midpoints: dict[str, float],
) -> np.ndarray:
    """
    Map BloodParameter objects onto a fixed-length feature vector.

    - Base features: filled from the report; missing ones use healthy defaults.
    - Derived ratio features: computed from report values when both are present,
      otherwise healthy-default ratios are used.
    - XGBoost handles NaN natively — absent features could also be passed as NaN,
      but healthy defaults produce more intuitive predictions for partial reports.
    """
    param_map = {p.name: p.value for p in params}

    # Compute derived ratios from actual report values where available
    def ratio(num: str, den: str) -> float:
        n = param_map.get(num)
        d = param_map.get(den)
        if n is not None and d is not None and d != 0:
            return n / d
        return _HEALTHY_DEFAULTS[f"{num}_{den}_ratio"
                                  if f"{num}_{den}_ratio" in _HEALTHY_DEFAULTS
                                  else "bun_creatinine_ratio"]  # fallback

    derived: dict[str, float] = {
        "bun_creatinine_ratio": (
            param_map["bun"] / param_map["creatinine"]
            if "bun" in param_map and "creatinine" in param_map and param_map["creatinine"] != 0
            else _HEALTHY_DEFAULTS["bun_creatinine_ratio"]
        ),
        "ast_alt_ratio": (
            param_map["ast"] / param_map["alt"]
            if "ast" in param_map and "alt" in param_map and param_map["alt"] != 0
            else _HEALTHY_DEFAULTS["ast_alt_ratio"]
        ),
        "mch_mcv_ratio": (
            param_map["mch"] / param_map["mcv"]
            if "mch" in param_map and "mcv" in param_map and param_map["mcv"] != 0
            else _HEALTHY_DEFAULTS["mch_mcv_ratio"]
        ),
        "hemoglobin_rbc_ratio": (
            param_map["hemoglobin"] / param_map["rbc"]
            if "hemoglobin" in param_map and "rbc" in param_map and param_map["rbc"] != 0
            else _HEALTHY_DEFAULTS["hemoglobin_rbc_ratio"]
        ),
    }

    lookup = {**param_map, **derived}

    vec = np.array(
        [lookup.get(name, _HEALTHY_DEFAULTS.get(name, midpoints.get(name, 0.0)))
         for name in feature_names],
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
