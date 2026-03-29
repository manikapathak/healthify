"""
TDD — Phase 4: Symptom-Based Risk Engine

All tests written BEFORE implementation. They should all FAIL until
backend/ml/risk_engine.py, data/symptom_condition_map.json, and
data/safety_conditions.json exist.
"""

import pytest

from backend.ml.zscore_detector import ParameterScore, Severity


def score(
    value: float,
    status: str,
    severity: str = "moderate",
    ref_low: float = 0.0,
    ref_high: float = 100.0,
    is_critical: bool = False,
) -> ParameterScore:
    return ParameterScore(
        value=value,
        unit="",
        z_score=0.0,
        status=status,
        severity=Severity(severity),
        ref_low=ref_low,
        ref_high=ref_high,
        is_critical=is_critical,
    )


# ---------------------------------------------------------------------------
# Import guard — fails until module exists
# ---------------------------------------------------------------------------

from backend.ml.risk_engine import (
    ConditionResult,
    RiskResult,
    assess_risk,
    load_knowledge_base,
    list_symptoms,
)


# ---------------------------------------------------------------------------
# Knowledge base loading
# ---------------------------------------------------------------------------

class TestKnowledgeBase:
    def test_loads_without_error(self):
        kb = load_knowledge_base()
        assert kb is not None

    def test_has_minimum_conditions(self):
        kb = load_knowledge_base()
        assert len(kb.conditions) >= 10

    def test_has_iron_deficiency_anemia(self):
        kb = load_knowledge_base()
        assert "iron_deficiency_anemia" in kb.conditions

    def test_has_type_2_diabetes(self):
        kb = load_knowledge_base()
        assert "type_2_diabetes" in kb.conditions

    def test_condition_has_required_fields(self):
        kb = load_knowledge_base()
        cond = kb.conditions["iron_deficiency_anemia"]
        assert hasattr(cond, "display_name")
        assert hasattr(cond, "blood_markers")
        assert hasattr(cond, "symptoms")
        assert hasattr(cond, "requires_doctor")
        assert hasattr(cond, "severity")

    def test_kb_is_cached(self):
        a = load_knowledge_base()
        b = load_knowledge_base()
        assert a is b

    def test_list_symptoms_returns_all_unique_symptoms(self):
        symptoms = list_symptoms()
        assert len(symptoms) > 0
        assert len(symptoms) == len(set(symptoms))  # no duplicates

    def test_symptom_names_are_snake_case(self):
        for sym in list_symptoms():
            assert sym == sym.lower()
            assert " " not in sym


# ---------------------------------------------------------------------------
# Risk scoring — classic patterns
# ---------------------------------------------------------------------------

class TestRiskScoring:
    def test_low_hb_low_mcv_with_fatigue_flags_anemia(self):
        anomalies = {
            "hemoglobin": score(9.0, "low", "severe", ref_low=12.0, ref_high=16.0),
            "mcv":        score(62.0, "low", "moderate", ref_low=80.0, ref_high=100.0),
        }
        result = assess_risk(anomalies, symptoms=["fatigue", "dizziness"], raw_values={"hemoglobin": 9.0})
        anemia = next((c for c in result.conditions if c.name == "iron_deficiency_anemia"), None)
        assert anemia is not None
        assert anemia.risk_percent >= 40

    def test_high_glucose_high_hba1c_flags_diabetes(self):
        anomalies = {
            "glucose": score(220.0, "high", "severe", ref_low=70.0, ref_high=100.0),
            "hba1c":   score(8.5, "high", "severe", ref_low=4.0, ref_high=5.6),
        }
        result = assess_risk(anomalies, symptoms=["excessive_thirst", "frequent_urination"], raw_values={"glucose": 220.0, "hba1c": 8.5})
        diabetes = next((c for c in result.conditions if c.name == "type_2_diabetes"), None)
        assert diabetes is not None
        assert diabetes.risk_percent >= 50

    def test_normal_values_no_symptoms_all_low_risk(self):
        result = assess_risk({}, symptoms=[], raw_values={})
        for cond in result.conditions:
            assert cond.risk_percent <= 15

    def test_risk_percent_always_0_to_100(self):
        anomalies = {
            "hemoglobin": score(5.0, "low", "severe", is_critical=True),
            "rbc":        score(2.0, "low", "severe"),
            "mcv":        score(55.0, "low", "severe"),
            "mch":        score(15.0, "low", "severe"),
            "ferritin":   score(2.0, "low", "severe"),
        }
        result = assess_risk(
            anomalies,
            symptoms=["fatigue", "dizziness", "pale_skin", "cold_hands_feet"],
            raw_values={"hemoglobin": 5.0},
        )
        for cond in result.conditions:
            assert 0 <= cond.risk_percent <= 100

    def test_conditions_sorted_by_risk_descending(self):
        anomalies = {
            "hemoglobin": score(9.0, "low", "severe", ref_low=12.0, ref_high=16.0),
            "mcv":        score(62.0, "low", "moderate"),
        }
        result = assess_risk(anomalies, symptoms=["fatigue"], raw_values={"hemoglobin": 9.0})
        percents = [c.risk_percent for c in result.conditions]
        assert percents == sorted(percents, reverse=True)

    def test_top_condition_matches_highest_risk(self):
        anomalies = {
            "hemoglobin": score(9.0, "low", "severe", ref_low=12.0, ref_high=16.0),
            "mcv":        score(62.0, "low", "moderate"),
        }
        result = assess_risk(anomalies, symptoms=["fatigue"], raw_values={"hemoglobin": 9.0})
        assert result.top_condition == result.conditions[0].name

    def test_result_has_required_fields(self):
        result = assess_risk({}, symptoms=[], raw_values={})
        assert hasattr(result, "conditions")
        assert hasattr(result, "requires_immediate_attention")
        assert hasattr(result, "top_condition")

    def test_condition_result_has_required_fields(self):
        result = assess_risk({}, symptoms=[], raw_values={})
        for cond in result.conditions:
            assert hasattr(cond, "name")
            assert hasattr(cond, "display_name")
            assert hasattr(cond, "risk_percent")
            assert hasattr(cond, "severity")
            assert hasattr(cond, "requires_doctor")
            assert hasattr(cond, "message")
            assert hasattr(cond, "lifestyle_tips")


# ---------------------------------------------------------------------------
# Safety layer
# ---------------------------------------------------------------------------

class TestSafetyLayer:
    def test_critical_glucose_triggers_immediate_attention(self):
        result = assess_risk(
            anomalies={"glucose": score(250.0, "high", "severe")},
            symptoms=[],
            raw_values={"glucose": 250.0},
        )
        assert result.requires_immediate_attention is True

    def test_critical_hemoglobin_triggers_immediate_attention(self):
        result = assess_risk(
            anomalies={"hemoglobin": score(5.5, "low", "severe", is_critical=True)},
            symptoms=[],
            raw_values={"hemoglobin": 5.5},
        )
        assert result.requires_immediate_attention is True

    def test_normal_values_no_immediate_attention(self):
        result = assess_risk({}, symptoms=[], raw_values={"glucose": 90.0, "hemoglobin": 14.0})
        assert result.requires_immediate_attention is False

    def test_borderline_glucose_no_immediate_attention(self):
        # 130 is high but not critically high
        result = assess_risk(
            anomalies={"glucose": score(130.0, "high", "borderline")},
            symptoms=[],
            raw_values={"glucose": 130.0},
        )
        assert result.requires_immediate_attention is False


# ---------------------------------------------------------------------------
# Doctor message + lifestyle tips
# ---------------------------------------------------------------------------

class TestMessages:
    def test_requires_doctor_condition_has_doctor_message(self):
        anomalies = {
            "hemoglobin": score(9.0, "low", "severe", ref_low=12.0, ref_high=16.0),
        }
        result = assess_risk(anomalies, symptoms=["fatigue"], raw_values={"hemoglobin": 9.0})
        anemia = next(c for c in result.conditions if c.name == "iron_deficiency_anemia")
        assert "doctor" in anemia.message.lower() or "physician" in anemia.message.lower() or "consult" in anemia.message.lower()

    def test_lifestyle_tips_only_for_low_risk_non_doctor_conditions(self):
        # No anomalies, no symptoms → all low risk
        result = assess_risk({}, symptoms=[], raw_values={})
        for cond in result.conditions:
            if cond.requires_doctor or cond.risk_percent >= 30:
                assert cond.lifestyle_tips == []
