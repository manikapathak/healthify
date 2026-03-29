"""
TDD — Phase 6: SHAP Explainability

Tests written BEFORE implementation. All should FAIL until
backend/ml/explainer.py exists.
"""

import pytest

from backend.core.parser import BloodParameter


def param(name: str, value: float, unit: str = "") -> BloodParameter:
    return BloodParameter(name=name, raw_name=name, value=value, unit=unit)


# ---------------------------------------------------------------------------
# Import guard — fails until module exists
# ---------------------------------------------------------------------------

from backend.ml.explainer import (
    ExplainResult,
    FeatureContribution,
    explain,
    load_explainer,
)


# ---------------------------------------------------------------------------
# Explainer loading
# ---------------------------------------------------------------------------

class TestExplainerLoading:
    def test_loads_without_error(self):
        exp = load_explainer()
        assert exp is not None

    def test_is_cached(self):
        a = load_explainer()
        b = load_explainer()
        assert a is b


# ---------------------------------------------------------------------------
# Result structure
# ---------------------------------------------------------------------------

class TestExplainResultStructure:
    def test_returns_explain_result(self):
        result = explain([param("hemoglobin", 14.0)], condition="healthy")
        assert isinstance(result, ExplainResult)

    def test_has_condition(self):
        result = explain([param("hemoglobin", 14.0)], condition="healthy")
        assert isinstance(result.condition, str)
        assert len(result.condition) > 0

    def test_has_contributions_list(self):
        result = explain([param("hemoglobin", 14.0)], condition="healthy")
        assert isinstance(result.contributions, list)

    def test_returns_at_most_5_contributions(self):
        params = [
            param("hemoglobin", 14.0),
            param("glucose", 90.0),
            param("wbc", 7000),
            param("mcv", 88.0),
            param("mch", 30.0),
            param("mchc", 34.0),
            param("hematocrit", 45.0),
        ]
        result = explain(params, condition="healthy")
        assert len(result.contributions) <= 5

    def test_contributions_sorted_by_absolute_value_descending(self):
        params = [
            param("hemoglobin", 8.0),
            param("mcv", 62.0),
            param("mch", 17.0),
            param("rbc", 3.0),
        ]
        result = explain(params, condition="iron_deficiency_anemia")
        values = [abs(c.contribution) for c in result.contributions]
        assert values == sorted(values, reverse=True)

    def test_each_contribution_has_required_fields(self):
        result = explain([param("hemoglobin", 14.0)], condition="healthy")
        for c in result.contributions:
            assert hasattr(c, "feature")
            assert hasattr(c, "contribution")
            assert hasattr(c, "direction")
            assert hasattr(c, "percentage")

    def test_direction_is_valid_value(self):
        result = explain([param("hemoglobin", 14.0)], condition="healthy")
        for c in result.contributions:
            assert c.direction in ("increases_risk", "decreases_risk")

    def test_percentage_is_string_with_percent_sign(self):
        result = explain([param("hemoglobin", 14.0)], condition="healthy")
        for c in result.contributions:
            assert isinstance(c.percentage, str)
            assert "%" in c.percentage

    def test_contribution_is_float(self):
        result = explain([param("hemoglobin", 14.0)], condition="healthy")
        for c in result.contributions:
            assert isinstance(c.contribution, float)

    def test_feature_names_are_canonical(self):
        result = explain([param("hemoglobin", 14.0)], condition="healthy")
        for c in result.contributions:
            assert c.feature == c.feature.lower()
            assert " " not in c.feature

    def test_empty_params_does_not_crash(self):
        result = explain([], condition="healthy")
        assert isinstance(result, ExplainResult)

    def test_unknown_condition_falls_back_gracefully(self):
        # Should not raise, falls back to top predicted class
        result = explain([param("hemoglobin", 14.0)], condition="xyz_not_a_real_condition")
        assert isinstance(result, ExplainResult)

    def test_inference_is_fast(self):
        import time
        params = [param("hemoglobin", 14.0), param("glucose", 90.0)]
        start = time.time()
        explain(params, condition="healthy")
        assert time.time() - start < 1.0


# ---------------------------------------------------------------------------
# Medical sanity checks
# ---------------------------------------------------------------------------

class TestExplainMedicalSanity:
    def test_anemia_pattern_hemoglobin_is_top_feature(self):
        params = [
            param("hemoglobin", 7.0),
            param("mcv", 60.0),
            param("mch", 16.0),
            param("rbc", 2.8),
            param("hematocrit", 22.0),
        ]
        result = explain(params, condition="iron_deficiency_anemia")
        if result.contributions:
            top_feature = result.contributions[0].feature
            # hemoglobin or a closely related CBC marker should dominate
            cbc_markers = {"hemoglobin", "mcv", "mch", "mchc", "rbc", "hematocrit"}
            assert top_feature in cbc_markers, (
                f"Expected a CBC marker as top feature for anemia, got: {top_feature}"
            )

    def test_diabetes_pattern_glucose_is_top_feature(self):
        params = [
            param("glucose", 250.0),
            param("hba1c", 9.5),
        ]
        result = explain(params, condition="type_2_diabetes")
        if result.contributions:
            top_feature = result.contributions[0].feature
            assert top_feature in {"glucose", "hba1c"}, (
                f"Expected glucose or hba1c as top feature for diabetes, got: {top_feature}"
            )
