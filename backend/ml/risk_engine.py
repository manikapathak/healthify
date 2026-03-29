"""
Symptom-based risk engine — Phase 4.

Scores each condition in the knowledge base using:
  - Blood marker anomalies (60% weight)
  - User-reported symptoms (40% weight)

Then applies a safety layer: if any raw blood value crosses a critical
threshold defined in safety_conditions.json, the result is flagged with
requires_immediate_attention=True regardless of the risk score.

Usage:
    from backend.ml.risk_engine import assess_risk, list_symptoms

    result = assess_risk(anomalies, symptoms=["fatigue", "dizziness"], raw_values={"hemoglobin": 9.0})
"""

from __future__ import annotations

import json
import operator
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from backend.ml.zscore_detector import ParameterScore

_CONDITION_FILE = Path(__file__).parent.parent.parent / "data" / "symptom_condition_map.json"
_SAFETY_FILE = Path(__file__).parent.parent.parent / "data" / "safety_conditions.json"

_OPS = {
    "gt": operator.gt,
    "lt": operator.lt,
    "gte": operator.ge,
    "lte": operator.le,
    "eq": operator.eq,
}

# Blood vs symptom contribution weights
_BLOOD_WEIGHT = 0.6
_SYMPTOM_WEIGHT = 0.4


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class BloodMarker:
    direction: str   # "low" or "high"
    weight: float


@dataclass(frozen=True)
class SymptomWeight:
    weight: float


@dataclass(frozen=True)
class Condition:
    name: str
    display_name: str
    blood_markers: dict[str, BloodMarker]
    symptoms: dict[str, SymptomWeight]
    severity: str
    requires_doctor: bool
    lifestyle_tips: list[str]


@dataclass(frozen=True)
class KnowledgeBase:
    conditions: dict[str, Condition]


@dataclass(frozen=True)
class SafetyThreshold:
    parameter: str
    operator: str
    value: float
    reason: str


@dataclass(frozen=True)
class ConditionResult:
    name: str
    display_name: str
    risk_percent: int
    severity: str
    requires_doctor: bool
    message: str
    lifestyle_tips: list[str]


@dataclass(frozen=True)
class RiskResult:
    conditions: list[ConditionResult]
    requires_immediate_attention: bool
    top_condition: str | None


# ---------------------------------------------------------------------------
# Loaders (cached)
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def load_knowledge_base() -> KnowledgeBase:
    raw = json.loads(_CONDITION_FILE.read_text())
    conditions: dict[str, Condition] = {}
    for name, data in raw.items():
        conditions[name] = Condition(
            name=name,
            display_name=data["display_name"],
            blood_markers={
                param: BloodMarker(direction=m["direction"], weight=m["weight"])
                for param, m in data["blood_markers"].items()
            },
            symptoms={
                sym: SymptomWeight(weight=s["weight"])
                for sym, s in data["symptoms"].items()
            },
            severity=data["severity"],
            requires_doctor=data["requires_doctor"],
            lifestyle_tips=data.get("lifestyle_tips", []),
        )
    return KnowledgeBase(conditions=conditions)


@lru_cache(maxsize=1)
def _load_safety_thresholds() -> list[SafetyThreshold]:
    raw = json.loads(_SAFETY_FILE.read_text())
    return [
        SafetyThreshold(
            parameter=t["parameter"],
            operator=t["operator"],
            value=t["value"],
            reason=t["reason"],
        )
        for t in raw["thresholds"]
    ]


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def list_symptoms() -> list[str]:
    """Return a sorted, deduplicated list of all symptom names in the knowledge base."""
    kb = load_knowledge_base()
    seen: set[str] = set()
    for cond in kb.conditions.values():
        seen.update(cond.symptoms.keys())
    return sorted(seen)


# ---------------------------------------------------------------------------
# Scoring helpers
# ---------------------------------------------------------------------------

def _blood_score(condition: Condition, anomalies: dict[str, ParameterScore]) -> float:
    """Sum of marker weights where the observed direction matches the condition's expected direction."""
    total_weight = sum(m.weight for m in condition.blood_markers.values())
    if total_weight == 0:
        return 0.0

    matched = 0.0
    for param, marker in condition.blood_markers.items():
        score = anomalies.get(param)
        if score is None:
            continue
        if score.status == marker.direction:   # "low" or "high"
            matched += marker.weight

    return matched / total_weight


def _symptom_score(condition: Condition, symptoms: list[str]) -> float:
    """Sum of symptom weights for user-selected symptoms, normalised to [0, 1]."""
    total_weight = sum(s.weight for s in condition.symptoms.values())
    if total_weight == 0:
        return 0.0

    matched = sum(
        condition.symptoms[sym].weight
        for sym in symptoms
        if sym in condition.symptoms
    )
    return matched / total_weight


def _check_safety(raw_values: dict[str, float]) -> bool:
    """Return True if any raw value crosses a critical safety threshold."""
    thresholds = _load_safety_thresholds()
    for threshold in thresholds:
        value = raw_values.get(threshold.parameter)
        if value is None:
            continue
        op_fn = _OPS.get(threshold.operator)
        if op_fn and op_fn(value, threshold.value):
            return True
    return False


def _build_message(condition: Condition, risk_percent: int) -> str:
    if condition.requires_doctor:
        return (
            "Based on these findings, a consultation with a physician is advisable "
            "to evaluate this further."
        )
    if risk_percent >= 30:
        return (
            "Consider discussing these findings with a healthcare professional "
            "at your next routine visit."
        )
    return "No specific action required at this time. Continue monitoring at regular check-ups."


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def assess_risk(
    anomalies: dict[str, ParameterScore],
    symptoms: list[str],
    raw_values: dict[str, float],
) -> RiskResult:
    """
    Score every condition in the knowledge base and return sorted results.

    Args:
        anomalies:   Output of detect_zscore — parameter name → ParameterScore.
                     Only anomalous parameters need to be included; normal ones
                     can be passed too and will simply contribute 0.
        symptoms:    List of canonical symptom name strings selected by the user.
        raw_values:  Raw numeric values keyed by canonical parameter name.
                     Used exclusively for safety threshold checking.

    Returns:
        RiskResult with conditions sorted by risk_percent descending.
    """
    kb = load_knowledge_base()
    requires_immediate = _check_safety(raw_values)

    results: list[ConditionResult] = []
    for name, condition in kb.conditions.items():
        blood = _blood_score(condition, anomalies)
        symptom = _symptom_score(condition, symptoms)
        raw_score = _BLOOD_WEIGHT * blood + _SYMPTOM_WEIGHT * symptom
        risk_percent = min(round(raw_score * 100), 100)

        # Lifestyle tips only shown for mild, non-doctor conditions
        tips = (
            condition.lifestyle_tips
            if not condition.requires_doctor and risk_percent < 30
            else []
        )

        results.append(ConditionResult(
            name=name,
            display_name=condition.display_name,
            risk_percent=risk_percent,
            severity=condition.severity,
            requires_doctor=condition.requires_doctor,
            message=_build_message(condition, risk_percent),
            lifestyle_tips=tips,
        ))

    results.sort(key=lambda c: c.risk_percent, reverse=True)
    top = results[0].name if results else None

    return RiskResult(
        conditions=results,
        requires_immediate_attention=requires_immediate,
        top_condition=top,
    )
