"""
TDD — Phase 2: Z-Score Detector

Tests written BEFORE implementation.
All tests should FAIL until zscore_detector.py is built.

Hand-calculated reference values used to verify correctness:

  Hemoglobin, adult_female: low=12.0, high=16.0
    mean = (12.0 + 16.0) / 2 = 14.0
    std  = (16.0 - 12.0) / 4 = 1.0
    value=14.0  → z =  0.0  → normal
    value=15.5  → z = +1.5  → borderline
    value=16.0  → z = +2.0  → moderate
    value=10.2  → z = -3.8  → severe
    value=12.0  → z = -2.0  → moderate
    value=13.0  → z = -1.0  → normal

  Glucose, adult_male: low=70.0, high=99.0
    mean = (70.0 + 99.0) / 2 = 84.5
    std  = (99.0 - 70.0) / 4 = 7.25
    value=84.5  → z =  0.0  → normal
    value=110.0 → z = +3.52 → severe
    value=77.0  → z = -1.03 → normal
"""

import pytest

from backend.core.parser import BloodParameter
from backend.ml.zscore_detector import (
    ZScoreDetector,
    ParameterScore,
    ZScoreResult,
    Severity,
    detect_zscore,
)


def param(name: str, value: float, unit: str = "") -> BloodParameter:
    return BloodParameter(name=name, raw_name=name, value=value, unit=unit)


# ---------------------------------------------------------------------------
# Severity classification
# ---------------------------------------------------------------------------

class TestSeverityClassification:
    def test_normal_below_1_5(self):
        d = ZScoreDetector()
        assert d.classify_severity(0.0) == Severity.NORMAL
        assert d.classify_severity(1.0) == Severity.NORMAL
        assert d.classify_severity(-1.4) == Severity.NORMAL

    def test_borderline_1_5_to_2(self):
        d = ZScoreDetector()
        assert d.classify_severity(1.5) == Severity.BORDERLINE
        assert d.classify_severity(-1.5) == Severity.BORDERLINE
        assert d.classify_severity(1.99) == Severity.BORDERLINE

    def test_moderate_2_to_3(self):
        d = ZScoreDetector()
        assert d.classify_severity(2.0) == Severity.MODERATE
        assert d.classify_severity(-2.5) == Severity.MODERATE
        assert d.classify_severity(2.99) == Severity.MODERATE

    def test_severe_3_plus(self):
        d = ZScoreDetector()
        assert d.classify_severity(3.0) == Severity.SEVERE
        assert d.classify_severity(-3.8) == Severity.SEVERE
        assert d.classify_severity(10.0) == Severity.SEVERE


# ---------------------------------------------------------------------------
# Z-score calculation (hand-verified)
# ---------------------------------------------------------------------------

class TestZScoreCalculation:
    def test_normal_value_z_near_zero(self):
        result = detect_zscore([param("hemoglobin", 14.0)], age=30, sex="female")
        score = result.scores["hemoglobin"]
        assert abs(score.z_score) < 0.1
        assert score.severity == Severity.NORMAL

    def test_borderline_high(self):
        # z = (15.5 - 14.0) / 1.0 = +1.5 → borderline
        # 15.5 < ref_high(16.0), so status is still "normal" by reference range.
        # Z-score detects the borderline deviation even while within range.
        result = detect_zscore([param("hemoglobin", 15.5)], age=30, sex="female")
        score = result.scores["hemoglobin"]
        assert abs(score.z_score - 1.5) < 0.05
        assert score.severity == Severity.BORDERLINE
        assert score.status == "normal"   # within range, but z-score flags it

    def test_moderate_at_ref_low(self):
        # z = (12.0 - 14.0) / 1.0 = -2.0 → moderate
        # 12.0 == ref_low (boundary uses strict <), so status="normal" by range.
        # Z-score still correctly flags it as moderate deviation.
        result = detect_zscore([param("hemoglobin", 12.0)], age=30, sex="female")
        score = result.scores["hemoglobin"]
        assert abs(score.z_score - (-2.0)) < 0.05
        assert score.severity == Severity.MODERATE

    def test_clearly_low_has_low_status(self):
        # value=10.0 < ref_low=12.0 → status="low" by reference range
        result = detect_zscore([param("hemoglobin", 10.0)], age=30, sex="female")
        score = result.scores["hemoglobin"]
        assert score.status == "low"
        assert score.severity in (Severity.MODERATE, Severity.SEVERE)

    def test_severe_low(self):
        # z = (10.2 - 14.0) / 1.0 = -3.8 → severe
        result = detect_zscore([param("hemoglobin", 10.2)], age=30, sex="female")
        score = result.scores["hemoglobin"]
        assert abs(score.z_score - (-3.8)) < 0.05
        assert score.severity == Severity.SEVERE

    def test_severe_high_glucose(self):
        # z = (110.0 - 84.5) / 7.25 = +3.52 → severe
        result = detect_zscore([param("glucose", 110.0)], age=30, sex="male")
        score = result.scores["glucose"]
        assert score.z_score > 3.0
        assert score.severity == Severity.SEVERE
        assert score.status == "high"

    def test_normal_glucose(self):
        result = detect_zscore([param("glucose", 84.5)], age=30, sex="male")
        score = result.scores["glucose"]
        assert abs(score.z_score) < 0.1
        assert score.severity == Severity.NORMAL

    def test_male_vs_female_different_ranges(self):
        # Hemoglobin male: low=13.5, high=17.5 → mean=15.5, std=1.0
        # Same value 14.0: male z=-1.5 (borderline), female z=0.0 (normal)
        male = detect_zscore([param("hemoglobin", 14.0)], age=30, sex="male")
        female = detect_zscore([param("hemoglobin", 14.0)], age=30, sex="female")
        assert male.scores["hemoglobin"].z_score < female.scores["hemoglobin"].z_score


# ---------------------------------------------------------------------------
# Unknown / missing parameters
# ---------------------------------------------------------------------------

class TestUnknownParameters:
    def test_unknown_param_skipped(self):
        result = detect_zscore([param("xyz_unknown", 99.0)], age=30, sex="male")
        assert "xyz_unknown" not in result.scores
        assert result.summary.total_parameters == 0

    def test_mixed_known_and_unknown(self):
        result = detect_zscore([
            param("hemoglobin", 14.0),
            param("xyz_unknown", 99.0),
        ], age=30, sex="female")
        assert "hemoglobin" in result.scores
        assert "xyz_unknown" not in result.scores
        assert result.summary.total_parameters == 1


# ---------------------------------------------------------------------------
# Summary statistics
# ---------------------------------------------------------------------------

class TestSummary:
    def test_anomaly_count(self):
        result = detect_zscore([
            param("hemoglobin", 14.0),   # normal
            param("glucose", 110.0),      # severe — anomaly
            param("cholesterol", 250.0),  # high — anomaly
        ], age=30, sex="male")
        assert result.summary.anomaly_count >= 2

    def test_severe_count(self):
        result = detect_zscore([
            param("hemoglobin", 10.2),   # severe
            param("glucose", 110.0),      # severe
        ], age=30, sex="female")
        assert result.summary.severe_count == 2

    def test_empty_parameters(self):
        result = detect_zscore([], age=30, sex="male")
        assert result.summary.total_parameters == 0
        assert result.summary.anomaly_count == 0
        assert result.scores == {}

    def test_all_normal_no_anomalies(self):
        # Male Hb mean=15.5 std=1.0 → use 15.5 (z=0.0)
        # Glucose male mean=84.5 → use 85.0 (z≈0.07)
        result = detect_zscore([
            param("hemoglobin", 15.5),
            param("glucose", 85.0),
        ], age=30, sex="male")
        assert result.summary.anomaly_count == 0

    def test_has_critical_flag(self):
        # Hemoglobin 5.0 is below critical_low=7.0
        result = detect_zscore([param("hemoglobin", 5.0)], age=30, sex="female")
        assert result.summary.has_critical is True

    def test_no_critical_for_normal(self):
        result = detect_zscore([param("hemoglobin", 14.0)], age=30, sex="female")
        assert result.summary.has_critical is False


# ---------------------------------------------------------------------------
# ParameterScore fields
# ---------------------------------------------------------------------------

class TestParameterScoreFields:
    def test_score_has_all_fields(self):
        result = detect_zscore([param("hemoglobin", 10.2, "g/dL")], age=30, sex="female")
        score = result.scores["hemoglobin"]
        assert isinstance(score, ParameterScore)
        assert score.value == 10.2
        assert score.unit == "g/dL"
        assert isinstance(score.z_score, float)
        assert score.status in ("low", "normal", "high")
        assert isinstance(score.severity, Severity)
        assert score.ref_low == 12.0
        assert score.ref_high == 16.0

    def test_result_is_immutable(self):
        result = detect_zscore([param("hemoglobin", 14.0)], age=30, sex="female")
        # ZScoreResult should be a frozen dataclass
        with pytest.raises(Exception):
            result.scores = {}
