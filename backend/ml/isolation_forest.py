"""
Isolation Forest anomaly detector — Phase 3.

Loads a pre-trained IsolationForest model from models/isolation_forest.joblib
and scores a set of blood parameters against it.

Usage:
    from backend.ml.isolation_forest import detect_isolation_forest, IFResult

    result = detect_isolation_forest(params, age=30, sex="male")
    print(result.anomaly_score, result.is_anomalous)
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Literal

import joblib
import numpy as np

from backend.core.parser import BloodParameter

_MODEL_FILE = Path(__file__).parent.parent.parent / "models" / "isolation_forest.joblib"


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ModelData:
    model: object          # sklearn IsolationForest
    scaler: object         # sklearn StandardScaler
    feature_names: list[str]
    midpoints: dict[str, float]   # canonical name → midpoint fill value


@dataclass(frozen=True)
class IFResult:
    anomaly_score: float   # higher = more normal (sklearn convention: score_samples)
    is_anomalous: bool
    confidence: Literal["high", "medium", "low"]


# ---------------------------------------------------------------------------
# Model loading (cached for process lifetime)
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def load_model() -> ModelData:
    """Load the trained IsolationForest artifact. Cached after first call."""
    data = joblib.load(_MODEL_FILE)
    return ModelData(
        model=data["model"],
        scaler=data["scaler"],
        feature_names=data["feature_names"],
        midpoints=data["midpoints"],
    )


# ---------------------------------------------------------------------------
# Feature vector construction
# ---------------------------------------------------------------------------

def build_feature_vector(
    params: list[BloodParameter],
    feature_names: list[str],
    age: int,
    sex: str,
    midpoints: dict[str, float] | None = None,
) -> np.ndarray:
    """
    Map a list of BloodParameter objects onto a fixed-length feature vector.

    Missing parameters are filled with the training-set column midpoint so
    that partial panels can still be scored without NaN contamination.
    """
    if midpoints is None:
        midpoints = load_model().midpoints

    param_map: dict[str, float] = {p.name: p.value for p in params}

    vec = np.array([
        param_map.get(name, midpoints.get(name, 0.0))
        for name in feature_names
    ], dtype=float)

    return vec


# ---------------------------------------------------------------------------
# Detection
# ---------------------------------------------------------------------------

# Threshold: sklearn's IsolationForest.score_samples returns values roughly in
# (-1, 0). Values below this threshold are considered anomalous.
_ANOMALY_THRESHOLD = -0.1


def detect_isolation_forest(
    params: list[BloodParameter],
    age: int,
    sex: str,
) -> IFResult:
    """
    Score a set of blood parameters with the trained IsolationForest.

    Returns an IFResult with:
        anomaly_score  — float, higher (less negative) = more normal
        is_anomalous   — bool, True when score < _ANOMALY_THRESHOLD
        confidence     — "high" if many features present, else "medium"/"low"
    """
    model_data = load_model()

    vec = build_feature_vector(
        params, model_data.feature_names, age, sex, model_data.midpoints
    )

    vec_scaled = model_data.scaler.transform(vec.reshape(1, -1))
    # decision_function = score_samples - offset_; positive = inlier, negative = anomaly
    score: float = float(model_data.model.decision_function(vec_scaled)[0])

    is_anomalous = score < _ANOMALY_THRESHOLD

    # Confidence based on how many features were actually provided vs. imputed
    provided = {p.name for p in params if p.name in model_data.feature_names}
    coverage = len(provided) / len(model_data.feature_names) if model_data.feature_names else 0.0

    if coverage >= 0.5:
        confidence: Literal["high", "medium", "low"] = "high"
    elif coverage >= 0.2:
        confidence = "medium"
    else:
        confidence = "low"

    return IFResult(
        anomaly_score=score,
        is_anomalous=is_anomalous,
        confidence=confidence,
    )
