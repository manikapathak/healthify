"""
Z-Score Anomaly Detector — Phase 2.

For each blood parameter, calculates a z-score relative to the age/sex-specific
reference range and classifies the deviation into a severity level.

Z-score formula:
    mean = (ref_high + ref_low) / 2
    std  = (ref_high - ref_low) / 4   ← 95% of healthy values fall within range
    z    = (value - mean) / std

Severity scale:
    |z| < 1.5          → normal
    1.5 ≤ |z| < 2.0   → borderline
    2.0 ≤ |z| < 3.0   → moderate
    |z| ≥ 3.0          → severe
"""

from dataclasses import dataclass
from enum import Enum

from backend.core.parser import BloodParameter
from backend.ml.reference_ranges import get_range


class Severity(str, Enum):
    NORMAL = "normal"
    BORDERLINE = "borderline"
    MODERATE = "moderate"
    SEVERE = "severe"


@dataclass(frozen=True)
class ParameterScore:
    value: float
    unit: str
    z_score: float
    status: str        # "low" | "normal" | "high"
    severity: Severity
    ref_low: float
    ref_high: float
    is_critical: bool


@dataclass(frozen=True)
class AnomalySummary:
    total_parameters: int
    anomaly_count: int      # borderline, moderate, or severe
    severe_count: int
    has_critical: bool


@dataclass(frozen=True)
class ZScoreResult:
    scores: dict[str, ParameterScore]
    summary: AnomalySummary


class ZScoreDetector:
    """Stateless detector — all methods are pure functions."""

    def classify_severity(self, z_score: float) -> Severity:
        abs_z = abs(z_score)
        if abs_z < 1.5:
            return Severity.NORMAL
        if abs_z < 2.0:
            return Severity.BORDERLINE
        if abs_z < 3.0:
            return Severity.MODERATE
        return Severity.SEVERE

    def score_parameter(
        self,
        param: BloodParameter,
        age: int,
        sex: str,
    ) -> ParameterScore | None:
        """
        Compute z-score for a single parameter.
        Returns None if the parameter has no reference range entry.
        """
        ref = get_range(param.name, age=age, sex=sex)
        if ref is None:
            return None

        mean = (ref.high + ref.low) / 2.0
        std = (ref.high - ref.low) / 4.0

        if std == 0:
            return None

        z = (param.value - mean) / std
        status = ref.classify(param.value)
        severity = self.classify_severity(z)
        is_critical = ref.is_critical(param.value)

        return ParameterScore(
            value=param.value,
            unit=param.unit or ref.unit,
            z_score=round(z, 4),
            status=status,
            severity=severity,
            ref_low=ref.low,
            ref_high=ref.high,
            is_critical=is_critical,
        )


def detect_zscore(
    parameters: list[BloodParameter],
    age: int = 30,
    sex: str = "male",
) -> ZScoreResult:
    """
    Run z-score detection on a list of blood parameters.

    Parameters without a reference range entry are silently skipped.
    Returns a frozen ZScoreResult.
    """
    detector = ZScoreDetector()
    scores: dict[str, ParameterScore] = {}

    for param in parameters:
        score = detector.score_parameter(param, age=age, sex=sex)
        if score is not None:
            scores[param.name] = score

    anomaly_count = sum(
        1 for s in scores.values() if s.severity != Severity.NORMAL
    )
    severe_count = sum(
        1 for s in scores.values() if s.severity == Severity.SEVERE
    )
    has_critical = any(s.is_critical for s in scores.values())

    summary = AnomalySummary(
        total_parameters=len(scores),
        anomaly_count=anomaly_count,
        severe_count=severe_count,
        has_critical=has_critical,
    )

    return ZScoreResult(scores=scores, summary=summary)
