"""
TDD — Phase 5: Logistic Regression Classifier

Tests written BEFORE implementation. All should FAIL until
backend/ml/classifier.py and models/classifier.joblib exist.
"""

import pytest
import numpy as np

from backend.core.parser import BloodParameter


def param(name: str, value: float, unit: str = "") -> BloodParameter:
    return BloodParameter(name=name, raw_name=name, value=value, unit=unit)


# ---------------------------------------------------------------------------
# Import guard — fails until module exists
# ---------------------------------------------------------------------------

from backend.ml.classifier import (
    ClassifierResult,
    ConditionProbability,
    load_classifier,
    build_feature_vector,
    predict,
)


# ---------------------------------------------------------------------------
# Model loading
# ---------------------------------------------------------------------------

class TestModelLoading:
    def test_loads_without_error(self):
        model_data = load_classifier()
        assert model_data is not None

    def test_has_feature_names(self):
        model_data = load_classifier()
        assert len(model_data.feature_names) > 0

    def test_has_classes(self):
        model_data = load_classifier()
        assert len(model_data.classes) > 0

    def test_classes_are_canonical_condition_names(self):
        model_data = load_classifier()
        for cls in model_data.classes:
            assert cls == cls.lower()
            assert " " not in cls

    def test_model_is_cached(self):
        a = load_classifier()
        b = load_classifier()
        assert a is b

    def test_healthy_class_present(self):
        model_data = load_classifier()
        assert "healthy" in model_data.classes

    def test_minimum_condition_classes(self):
        # Should know at least 5 conditions beyond healthy
        model_data = load_classifier()
        non_healthy = [c for c in model_data.classes if c != "healthy"]
        assert len(non_healthy) >= 4


# ---------------------------------------------------------------------------
# Feature vector construction
# ---------------------------------------------------------------------------

class TestFeatureVector:
    def test_vector_length_matches_features(self):
        model_data = load_classifier()
        params = [param("hemoglobin", 14.0), param("glucose", 90.0)]
        vec = build_feature_vector(params, model_data.feature_names, model_data.midpoints)
        assert len(vec) == len(model_data.feature_names)

    def test_no_nan_in_vector(self):
        model_data = load_classifier()
        params = [param("hemoglobin", 14.0)]
        vec = build_feature_vector(params, model_data.feature_names, model_data.midpoints)
        assert not any(np.isnan(vec))

    def test_empty_params_uses_midpoints(self):
        model_data = load_classifier()
        vec = build_feature_vector([], model_data.feature_names, model_data.midpoints)
        assert len(vec) == len(model_data.feature_names)
        assert not any(np.isnan(vec))

    def test_unknown_params_ignored(self):
        model_data = load_classifier()
        params = [param("xyz_unknown", 99.0)]
        vec = build_feature_vector(params, model_data.feature_names, model_data.midpoints)
        assert len(vec) == len(model_data.feature_names)


# ---------------------------------------------------------------------------
# Prediction — result structure
# ---------------------------------------------------------------------------

class TestPredictionStructure:
    def test_returns_classifier_result(self):
        params = [param("hemoglobin", 14.0), param("glucose", 90.0)]
        result = predict(params)
        assert isinstance(result, ClassifierResult)

    def test_has_top_condition(self):
        result = predict([param("hemoglobin", 14.0)])
        assert isinstance(result.top_condition, str)
        assert len(result.top_condition) > 0

    def test_has_top_probability(self):
        result = predict([param("hemoglobin", 14.0)])
        assert isinstance(result.top_probability, float)
        assert 0.0 <= result.top_probability <= 1.0

    def test_has_all_probabilities(self):
        result = predict([param("hemoglobin", 14.0)])
        assert isinstance(result.probabilities, list)
        assert len(result.probabilities) > 0

    def test_probabilities_sum_to_one(self):
        result = predict([param("hemoglobin", 14.0)])
        total = sum(cp.probability for cp in result.probabilities)
        assert abs(total - 1.0) < 0.01

    def test_probabilities_sorted_descending(self):
        result = predict([param("hemoglobin", 14.0)])
        probs = [cp.probability for cp in result.probabilities]
        assert probs == sorted(probs, reverse=True)

    def test_top_condition_matches_highest_probability(self):
        result = predict([param("hemoglobin", 14.0)])
        assert result.top_condition == result.probabilities[0].condition

    def test_condition_probability_has_required_fields(self):
        result = predict([param("hemoglobin", 14.0)])
        for cp in result.probabilities:
            assert hasattr(cp, "condition")
            assert hasattr(cp, "probability")
            assert hasattr(cp, "display_name")

    def test_inference_is_fast(self):
        import time
        params = [param("hemoglobin", 14.0), param("glucose", 90.0), param("wbc", 7000)]
        start = time.time()
        predict(params)
        assert time.time() - start < 0.5


# ---------------------------------------------------------------------------
# Prediction — medical sanity checks
# ---------------------------------------------------------------------------

class TestPredictionSanity:
    def test_normal_cbc_predicts_healthy_in_top3(self):
        params = [
            param("hemoglobin", 15.0),
            param("rbc", 5.0),
            param("wbc", 7000),
            param("platelets", 250000),
            param("mcv", 88.0),
            param("mch", 30.0),
            param("mchc", 34.0),
            param("hematocrit", 45.0),
        ]
        result = predict(params)
        top3 = [cp.condition for cp in result.probabilities[:3]]
        assert "healthy" in top3, f"healthy not in top 3: {top3}"

    def test_anemia_pattern_predicts_anemia_condition(self):
        # Classic iron-deficiency anemia pattern
        params = [
            param("hemoglobin", 8.0),
            param("mcv", 62.0),
            param("mch", 17.0),
            param("mchc", 28.0),
            param("rbc", 3.0),
            param("hematocrit", 25.0),
        ]
        result = predict(params)
        anemia_conditions = {
            "iron_deficiency_anemia", "normocytic_hypochromic_anemia",
            "normocytic_normochromic_anemia", "microcytic_anemia", "macrocytic_anemia"
        }
        top3 = {cp.condition for cp in result.probabilities[:3]}
        assert top3 & anemia_conditions, f"No anemia in top 3: {top3}"

    def test_high_glucose_hba1c_predicts_diabetes_in_top3(self):
        params = [
            param("glucose", 240.0),
            param("hba1c", 9.0),
        ]
        result = predict(params)
        top3 = [cp.condition for cp in result.probabilities[:3]]
        assert "type_2_diabetes" in top3, f"type_2_diabetes not in top 3: {top3}"
