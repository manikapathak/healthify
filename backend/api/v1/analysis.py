import structlog
from fastapi import APIRouter

logger = structlog.get_logger()

from backend.api.schemas.analysis import (
    AnomalySummaryOut,
    CompareResultOut,
    ConditionProbabilityOut,
    ExplainRequest,
    ExplainResultOut,
    FeatureContributionOut,
    IFRequest,
    IFResultOut,
    MLPredictionOut,
    ParameterScoreOut,
    PredictRequest,
    PredictResultOut,
    RuleBasedSummaryOut,
    ZScoreRequest,
    ZScoreResultOut,
)
from backend.api.schemas.common import APIResponse
from backend.core.disclaimer import get_disclaimer
from backend.core.parser import BloodParameter
from backend.ml.classifier import ClassifierResult, predict as classify
from backend.ml.explainer import explain
from backend.ml.isolation_forest import IFResult, detect_isolation_forest
from backend.ml.risk_engine import assess_risk
from backend.ml.zscore_detector import AnomalySummary, ParameterScore, detect_zscore

router = APIRouter()


def _score_to_out(score: ParameterScore) -> ParameterScoreOut:
    return ParameterScoreOut(
        value=score.value,
        unit=score.unit,
        z_score=score.z_score,
        status=score.status,
        severity=score.severity.value,
        ref_low=score.ref_low,
        ref_high=score.ref_high,
        is_critical=score.is_critical,
    )


def _summary_to_out(summary: AnomalySummary) -> AnomalySummaryOut:
    return AnomalySummaryOut(
        total_parameters=summary.total_parameters,
        anomaly_count=summary.anomaly_count,
        severe_count=summary.severe_count,
        has_critical=summary.has_critical,
    )


def _to_result_out(scores: dict, summary: AnomalySummary) -> ZScoreResultOut:
    return ZScoreResultOut(
        scores={name: _score_to_out(score) for name, score in scores.items()},
        summary=_summary_to_out(summary),
    )


def _if_result_to_out(result: IFResult) -> IFResultOut:
    return IFResultOut(
        anomaly_score=result.anomaly_score,
        is_anomalous=result.is_anomalous,
        confidence=result.confidence,
    )


@router.post("/zscore", response_model=APIResponse[ZScoreResultOut])
async def zscore_analysis(req: ZScoreRequest) -> APIResponse[ZScoreResultOut]:
    """
    Run Z-score anomaly detection on blood parameters.

    Returns a severity score for each recognized parameter and a summary
    of how many anomalies were found.
    """
    try:
        params = [
            BloodParameter(name=p.name, raw_name=p.name, value=p.value, unit=p.unit)
            for p in req.parameters
        ]

        result = detect_zscore(params, age=req.age, sex=req.sex)

        disclaimer = get_disclaimer(
            has_critical=result.summary.has_critical,
            anomaly_count=result.summary.anomaly_count,
        )

        return APIResponse(
            success=True,
            data=_to_result_out(result.scores, result.summary),
            disclaimer=disclaimer,
        )
    except Exception as exc:
        logger.error("zscore_analysis_failed", error=str(exc))
        return APIResponse.fail(f"Z-score analysis failed: {exc}")


@router.post("/isolation-forest", response_model=APIResponse[IFResultOut])
async def isolation_forest_analysis(req: IFRequest) -> APIResponse[IFResultOut]:
    """
    Run Isolation Forest anomaly detection on blood parameters.

    Returns a continuous anomaly score (positive = normal, negative = anomalous),
    a boolean flag, and a confidence level based on parameter coverage.
    """
    try:
        params = [
            BloodParameter(name=p.name, raw_name=p.name, value=p.value, unit=p.unit)
            for p in req.parameters
        ]

        result = detect_isolation_forest(params, age=req.age, sex=req.sex)

        disclaimer = get_disclaimer(
            has_critical=False,
            anomaly_count=1 if result.is_anomalous else 0,
        )

        return APIResponse(
            success=True,
            data=_if_result_to_out(result),
            disclaimer=disclaimer,
        )
    except Exception as exc:
        logger.error("isolation_forest_analysis_failed", error=str(exc))
        return APIResponse.fail(f"Isolation Forest analysis failed: {exc}")


@router.post("/compare", response_model=APIResponse[CompareResultOut])
async def compare_analysis(req: IFRequest) -> APIResponse[CompareResultOut]:
    """
    Run both Z-score and Isolation Forest detectors and return a side-by-side comparison.

    The `agreement` field indicates whether both methods classify the sample
    the same way (both anomalous or both normal).
    """
    try:
        params = [
            BloodParameter(name=p.name, raw_name=p.name, value=p.value, unit=p.unit)
            for p in req.parameters
        ]

        zscore_result = detect_zscore(params, age=req.age, sex=req.sex)
        if_result = detect_isolation_forest(params, age=req.age, sex=req.sex)

        zscore_anomalous = zscore_result.summary.anomaly_count > 0

        disclaimer = get_disclaimer(
            has_critical=zscore_result.summary.has_critical,
            anomaly_count=zscore_result.summary.anomaly_count,
        )

        return APIResponse(
            success=True,
            data=CompareResultOut(
                zscore=_to_result_out(zscore_result.scores, zscore_result.summary),
                isolation_forest=_if_result_to_out(if_result),
                agreement=(zscore_anomalous == if_result.is_anomalous),
            ),
            disclaimer=disclaimer,
        )
    except Exception as exc:
        logger.error("compare_analysis_failed", error=str(exc))
        return APIResponse.fail(f"Compare analysis failed: {exc}")


@router.post("/predict", response_model=APIResponse[PredictResultOut])
async def predict_analysis(req: PredictRequest) -> APIResponse[PredictResultOut]:
    """
    Run the Logistic Regression classifier alongside the rule-based risk engine
    and return a side-by-side comparison.

    - `ml_prediction` — probabilities per condition from the trained LR model
    - `rule_based` — top condition and risk % from the Phase 4 symptom engine
    - `agreement` — True when both methods pick the same top condition
    - `confidence` — "high" when agreement, "low" when they disagree
    """
    try:
        params = [
            BloodParameter(name=p.name, raw_name=p.name, value=p.value, unit=p.unit)
            for p in req.parameters
        ]

        # ML prediction
        ml_result = classify(params)

        # Rule-based prediction (uses z-score internally)
        zscore_result = detect_zscore(params, age=req.age, sex=req.sex)
        raw_values = {p.name: p.value for p in params}
        risk_result = assess_risk(
            anomalies=zscore_result.scores,
            symptoms=req.symptoms,
            raw_values=raw_values,
        )

        top_rule = risk_result.top_condition
        top_rule_risk = (
            next(c.risk_percent for c in risk_result.conditions if c.name == top_rule)
            if top_rule else 0
        )

        agreement = ml_result.top_condition == top_rule
        confidence = "high" if agreement else "low"

        disclaimer = get_disclaimer(
            has_critical=zscore_result.summary.has_critical,
            anomaly_count=zscore_result.summary.anomaly_count,
        )

        return APIResponse(
            success=True,
            data=PredictResultOut(
                ml_prediction=MLPredictionOut(
                    top_condition=ml_result.top_condition,
                    top_probability=ml_result.top_probability,
                    probabilities=[
                        ConditionProbabilityOut(
                            condition=cp.condition,
                            display_name=cp.display_name,
                            probability=cp.probability,
                        )
                        for cp in ml_result.probabilities
                    ],
                ),
                rule_based=RuleBasedSummaryOut(
                    top_condition=top_rule,
                    risk_percent=top_rule_risk,
                ),
                agreement=agreement,
                confidence=confidence,
            ),
            disclaimer=disclaimer,
        )
    except Exception as exc:
        logger.error("predict_analysis_failed", error=str(exc))
        return APIResponse.fail(f"Predict analysis failed: {exc}")


@router.post("/explain", response_model=APIResponse[ExplainResultOut])
async def explain_analysis(req: ExplainRequest) -> APIResponse[ExplainResultOut]:
    """
    Return a SHAP-based explanation for the top (or requested) condition.

    For each prediction, shows the top 5 blood parameters that contributed
    most to the risk score, with direction and percentage contribution.

    - `prediction` — ML model output (same as /predict)
    - `explained_condition` — which condition was explained
    - `explanations` — up to 5 features sorted by |contribution| descending
    """
    try:
        params = [
            BloodParameter(name=p.name, raw_name=p.name, value=p.value, unit=p.unit)
            for p in req.parameters
        ]

        ml_result = classify(params)
        explain_result = explain(params, condition=req.condition)

        zscore_result = detect_zscore(params, age=req.age, sex=req.sex)
        disclaimer = get_disclaimer(
            has_critical=zscore_result.summary.has_critical,
            anomaly_count=zscore_result.summary.anomaly_count,
        )

        return APIResponse(
            success=True,
            data=ExplainResultOut(
                prediction=MLPredictionOut(
                    top_condition=ml_result.top_condition,
                    top_probability=ml_result.top_probability,
                    probabilities=[
                        ConditionProbabilityOut(
                            condition=cp.condition,
                            display_name=cp.display_name,
                            probability=cp.probability,
                        )
                        for cp in ml_result.probabilities
                    ],
                ),
                explained_condition=explain_result.condition,
                explanations=[
                    FeatureContributionOut(
                        feature=c.feature,
                        contribution=c.contribution,
                        direction=c.direction,
                        percentage=c.percentage,
                    )
                    for c in explain_result.contributions
                ],
            ),
            disclaimer=disclaimer,
        )
    except Exception as exc:
        logger.error("explain_analysis_failed", error=str(exc))
        return APIResponse.fail(f"Explain analysis failed: {exc}")
