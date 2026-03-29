"""
TDD — Phase 3: Isolation Forest Detector

Tests written BEFORE implementation. All should FAIL until
isolation_forest.py and training_data.csv exist.
"""

import numpy as np
import pytest

from backend.core.parser import BloodParameter


def param(name: str, value: float, unit: str = "") -> BloodParameter:
    return BloodParameter(name=name, raw_name=name, value=value, unit=unit)


# ---------------------------------------------------------------------------
# Import guard — will fail until module exists
# ---------------------------------------------------------------------------

from backend.ml.isolation_forest import (
    IFResult,
    detect_isolation_forest,
    load_model,
)


# ---------------------------------------------------------------------------
# Model loading
# ---------------------------------------------------------------------------

class TestModelLoading:
    def test_model_loads_without_error(self):
        model_data = load_model()
        assert model_data is not None

    def test_model_has_feature_names(self):
        model_data = load_model()
        assert len(model_data.feature_names) > 0

    def test_feature_names_are_canonical(self):
        model_data = load_model()
        # All feature names should be lowercase with underscores
        for name in model_data.feature_names:
            assert name == name.lower()
            assert " " not in name

    def test_model_is_cached(self):
        # Calling twice should return same object (cached)
        a = load_model()
        b = load_model()
        assert a is b


# ---------------------------------------------------------------------------
# Feature vector construction
# ---------------------------------------------------------------------------

from backend.ml.isolation_forest import build_feature_vector

class TestFeatureVector:
    def test_known_params_placed_correctly(self):
        model_data = load_model()
        params = [param("hemoglobin", 14.0, "g/dL")]
        vec = build_feature_vector(params, model_data.feature_names, age=30, sex="male")
        assert len(vec) == len(model_data.feature_names)

    def test_missing_params_filled_with_midpoint(self):
        model_data = load_model()
        # Pass empty params — all values should be filled with midpoint (not NaN)
        vec = build_feature_vector([], model_data.feature_names, age=30, sex="male")
        assert not any(np.isnan(vec)), "Missing params should be filled, not NaN"

    def test_vector_length_matches_features(self):
        model_data = load_model()
        params = [
            param("hemoglobin", 14.0),
            param("glucose", 90.0),
        ]
        vec = build_feature_vector(params, model_data.feature_names, age=30, sex="male")
        assert len(vec) == len(model_data.feature_names)


# ---------------------------------------------------------------------------
# Detection — normal samples
# ---------------------------------------------------------------------------

class TestNormalDetection:
    def test_clearly_normal_cbc_not_flagged(self):
        # Textbook normal CBC values
        normal_params = [
            param("hemoglobin", 15.0),
            param("rbc", 5.0),
            param("wbc", 7000),
            param("platelets", 250000),
            param("mcv", 88.0),
            param("mch", 30.0),
            param("mchc", 34.0),
            param("hematocrit", 45.0),
        ]
        result = detect_isolation_forest(normal_params, age=30, sex="male")
        assert isinstance(result, IFResult)
        # Normal sample should have a positive or near-zero anomaly score
        assert result.anomaly_score > -0.2, (
            f"Normal CBC should not be strongly anomalous, got score={result.anomaly_score}"
        )

    def test_result_has_required_fields(self):
        result = detect_isolation_forest([param("hemoglobin", 14.5)], age=30, sex="female")
        assert hasattr(result, "anomaly_score")
        assert hasattr(result, "is_anomalous")
        assert hasattr(result, "confidence")

    def test_anomaly_score_is_float(self):
        result = detect_isolation_forest([param("glucose", 90.0)], age=30, sex="male")
        assert isinstance(result.anomaly_score, float)

    def test_is_anomalous_is_bool(self):
        result = detect_isolation_forest([param("hemoglobin", 14.0)], age=30, sex="male")
        assert isinstance(result.is_anomalous, bool)

    def test_confidence_valid_value(self):
        result = detect_isolation_forest([param("hemoglobin", 14.0)], age=30, sex="male")
        assert result.confidence in ("high", "medium", "low")


# ---------------------------------------------------------------------------
# Detection — anomalous samples
# ---------------------------------------------------------------------------

class TestAnomalousDetection:
    def test_severe_anemia_pattern_flagged(self):
        # Classic severe iron deficiency anemia — multiple markers very low together
        anemia_params = [
            param("hemoglobin", 6.5),     # far below normal
            param("rbc", 2.8),            # low
            param("mcv", 62.0),           # microcytic
            param("mch", 18.0),           # low
            param("platelets", 420000),
            param("wbc", 8000),
        ]
        result = detect_isolation_forest(anemia_params, age=30, sex="female")
        # Severe anemia should produce a more negative score than normal
        assert result.anomaly_score < 0.1, (
            f"Severe anemia pattern should be flagged, got score={result.anomaly_score}"
        )

    def test_anomaly_score_lower_for_abnormal_than_normal(self):
        normal = detect_isolation_forest([
            param("hemoglobin", 15.0),
            param("wbc", 7000),
            param("platelets", 250000),
        ], age=30, sex="male")

        abnormal = detect_isolation_forest([
            param("hemoglobin", 6.0),    # critically low
            param("wbc", 95000),         # critically high
            param("platelets", 30000),   # critically low
        ], age=30, sex="male")

        assert normal.anomaly_score > abnormal.anomaly_score, (
            "Normal sample should have higher (less negative) score than abnormal"
        )


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_empty_params_does_not_crash(self):
        result = detect_isolation_forest([], age=30, sex="male")
        assert isinstance(result, IFResult)

    def test_single_param_does_not_crash(self):
        result = detect_isolation_forest([param("glucose", 90.0)], age=30, sex="male")
        assert isinstance(result, IFResult)

    def test_unknown_params_ignored(self):
        result = detect_isolation_forest(
            [param("xyz_unknown_param", 99.0)],
            age=30, sex="male"
        )
        assert isinstance(result, IFResult)

    def test_inference_is_fast(self):
        import time
        params = [
            param("hemoglobin", 14.0),
            param("glucose", 90.0),
            param("wbc", 7000),
        ]
        start = time.time()
        detect_isolation_forest(params, age=30, sex="male")
        elapsed = time.time() - start
        assert elapsed < 0.5, f"Inference took {elapsed:.2f}s, expected < 0.5s"
