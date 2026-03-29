"""
Risk assessment endpoints — Phase 4.

GET  /api/v1/risk/symptoms   — list all known symptom names
POST /api/v1/risk/assess     — score conditions from blood anomalies + symptoms
"""

import structlog
from fastapi import APIRouter

from backend.api.schemas.common import APIResponse
from backend.api.schemas.risk import ConditionResultOut, RiskAssessRequest, RiskResultOut
from backend.core.disclaimer import DISCLAIMER_CRITICAL, get_disclaimer
from backend.core.parser import BloodParameter
from backend.ml.risk_engine import ConditionResult, RiskResult, assess_risk, list_symptoms
from backend.ml.zscore_detector import detect_zscore

logger = structlog.get_logger()
router = APIRouter()


def _condition_to_out(c: ConditionResult) -> ConditionResultOut:
    return ConditionResultOut(
        name=c.name,
        display_name=c.display_name,
        risk_percent=c.risk_percent,
        severity=c.severity,
        requires_doctor=c.requires_doctor,
        message=c.message,
        lifestyle_tips=c.lifestyle_tips,
    )


def _result_to_out(result: RiskResult) -> RiskResultOut:
    return RiskResultOut(
        conditions=[_condition_to_out(c) for c in result.conditions],
        requires_immediate_attention=result.requires_immediate_attention,
        top_condition=result.top_condition,
    )


@router.get("/symptoms", response_model=APIResponse[list[str]])
async def get_symptoms() -> APIResponse[list[str]]:
    """
    Return a sorted list of all symptom names understood by the risk engine.

    Use these exact strings in the `symptoms` field of POST /risk/assess.
    """
    try:
        return APIResponse(success=True, data=list_symptoms())
    except Exception as exc:
        logger.error("list_symptoms_failed", error=str(exc))
        return APIResponse.fail(f"Failed to list symptoms: {exc}")


@router.post("/assess", response_model=APIResponse[RiskResultOut])
async def assess(req: RiskAssessRequest) -> APIResponse[RiskResultOut]:
    """
    Calculate condition risk scores from blood parameters and user-reported symptoms.

    Steps:
    1. Run Z-score detection to identify anomalous parameters.
    2. Pass anomalies + symptoms to the risk engine.
    3. Apply safety layer — flag if any value crosses a critical threshold.
    4. Return conditions sorted by risk_percent descending.
    """
    try:
        params = [
            BloodParameter(name=p.name, raw_name=p.name, value=p.value, unit=p.unit)
            for p in req.parameters
        ]

        zscore_result = detect_zscore(params, age=req.age, sex=req.sex)

        raw_values = {p.name: p.value for p in params}

        result = assess_risk(
            anomalies=zscore_result.scores,
            symptoms=req.symptoms,
            raw_values=raw_values,
        )

        if result.requires_immediate_attention:
            disclaimer = DISCLAIMER_CRITICAL
        else:
            disclaimer = get_disclaimer(
                has_critical=zscore_result.summary.has_critical,
                anomaly_count=zscore_result.summary.anomaly_count,
            )

        return APIResponse(
            success=True,
            data=_result_to_out(result),
            disclaimer=disclaimer,
        )
    except Exception as exc:
        logger.error("risk_assess_failed", error=str(exc))
        return APIResponse.fail(f"Risk assessment failed: {exc}")
