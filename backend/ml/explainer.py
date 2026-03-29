"""
SHAP Explainability — Phase 6.

Uses shap.LinearExplainer on the trained Logistic Regression model to compute
per-feature contributions for a specific condition class.

Usage:
    from backend.ml.explainer import explain, ExplainResult

    result = explain(params, condition="iron_deficiency_anemia")
    for c in result.contributions:
        print(c.feature, c.direction, c.percentage)
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

import numpy as np
import shap

from backend.core.parser import BloodParameter
from backend.ml.classifier import (
    build_feature_vector,
    load_classifier,
    predict,
)

_TOP_N = 5


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class FeatureContribution:
    feature: str
    contribution: float          # raw SHAP value for the target class
    direction: str               # "increases_risk" or "decreases_risk"
    percentage: str              # e.g. "32%"


@dataclass(frozen=True)
class ExplainResult:
    condition: str               # condition being explained
    contributions: list[FeatureContribution]   # top N, sorted by |contribution| desc


# ---------------------------------------------------------------------------
# Explainer loading (cached)
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def load_explainer() -> shap.LinearExplainer:
    """Build and cache a SHAP LinearExplainer from the trained classifier."""
    model_data = load_classifier()
    explainer = shap.LinearExplainer(
        model_data.model,
        masker=shap.maskers.Independent(
            data=np.zeros((1, len(model_data.feature_names)))
        ),
    )
    return explainer


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def explain(
    params: list[BloodParameter],
    condition: str | None = None,
) -> ExplainResult:
    """
    Compute SHAP feature contributions for a specific condition class.

    Args:
        params:     Blood parameters from the user.
        condition:  Canonical condition name to explain (e.g. "iron_deficiency_anemia").
                    If None or not found in the model's classes, the top predicted
                    condition is used automatically.

    Returns:
        ExplainResult with up to 5 features sorted by |contribution| descending.
    """
    model_data = load_classifier()

    # Build and scale the feature vector
    vec = build_feature_vector(params, model_data.feature_names, model_data.midpoints)
    vec_scaled = model_data.scaler.transform(vec.reshape(1, -1))

    # Resolve which condition class index to explain
    classes = model_data.classes
    if condition and condition in classes:
        target_condition = condition
    else:
        # Fall back to top predicted class
        ml_result = predict(params)
        target_condition = ml_result.top_condition

    class_idx = classes.index(target_condition)

    # Compute SHAP values — shape: (n_classes, n_samples, n_features)
    explainer = load_explainer()
    shap_values = explainer.shap_values(vec_scaled)

    # LinearExplainer returns (n_samples, n_features, n_classes) or a list per class
    if isinstance(shap_values, list):
        # older shap: list of (n_samples, n_features) — one array per class
        class_shap = np.array(shap_values[class_idx])[0]
    else:
        sv = np.array(shap_values)
        if sv.ndim == 3:
            # (n_samples, n_features, n_classes)
            class_shap = sv[0, :, class_idx]
        else:
            # (n_samples, n_features) — binary case
            class_shap = sv[0]

    feature_names = model_data.feature_names

    # Compute total absolute contribution for percentage calculation
    total_abs = float(np.abs(class_shap).sum())
    if total_abs == 0:
        total_abs = 1.0   # avoid division by zero

    # Build sorted contributions
    indexed = sorted(
        enumerate(class_shap),
        key=lambda x: abs(x[1]),
        reverse=True,
    )

    contributions: list[FeatureContribution] = []
    for feat_idx, shap_val in indexed[:_TOP_N]:
        raw = float(shap_val)
        pct = round(abs(raw) / total_abs * 100)
        contributions.append(FeatureContribution(
            feature=feature_names[feat_idx],
            contribution=round(raw, 4),
            direction="increases_risk" if raw > 0 else "decreases_risk",
            percentage=f"{pct}%",
        ))

    return ExplainResult(
        condition=target_condition,
        contributions=contributions,
    )
