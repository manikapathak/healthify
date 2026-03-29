from pydantic import BaseModel, Field


class ParameterInput(BaseModel):
    name: str
    value: float
    unit: str = ""


class ZScoreRequest(BaseModel):
    parameters: list[ParameterInput] = Field(default_factory=list)
    age: int = Field(default=30, ge=0, le=120)
    sex: str = Field(default="male", pattern="^(male|female)$")


class ParameterScoreOut(BaseModel):
    value: float
    unit: str
    z_score: float
    status: str
    severity: str
    ref_low: float
    ref_high: float
    is_critical: bool


class AnomalySummaryOut(BaseModel):
    total_parameters: int
    anomaly_count: int
    severe_count: int
    has_critical: bool


class ZScoreResultOut(BaseModel):
    scores: dict[str, ParameterScoreOut]
    summary: AnomalySummaryOut


# ---------------------------------------------------------------------------
# Isolation Forest schemas
# ---------------------------------------------------------------------------

class IFRequest(BaseModel):
    parameters: list[ParameterInput] = Field(default_factory=list)
    age: int = Field(default=30, ge=0, le=120)
    sex: str = Field(default="male", pattern="^(male|female)$")


class IFResultOut(BaseModel):
    anomaly_score: float
    is_anomalous: bool
    confidence: str


# ---------------------------------------------------------------------------
# Compare schemas
# ---------------------------------------------------------------------------

class CompareResultOut(BaseModel):
    zscore: ZScoreResultOut
    isolation_forest: IFResultOut
    agreement: bool   # both methods agree on anomalous/normal


# ---------------------------------------------------------------------------
# Classifier / Predict schemas
# ---------------------------------------------------------------------------

class ConditionProbabilityOut(BaseModel):
    condition: str
    display_name: str
    probability: float


class MLPredictionOut(BaseModel):
    top_condition: str
    top_probability: float
    probabilities: list[ConditionProbabilityOut]


class RuleBasedSummaryOut(BaseModel):
    top_condition: str | None
    risk_percent: int


class PredictRequest(BaseModel):
    parameters: list[ParameterInput] = Field(default_factory=list)
    age: int = Field(default=30, ge=0, le=120)
    sex: str = Field(default="male", pattern="^(male|female)$")
    symptoms: list[str] = Field(default_factory=list)


class PredictResultOut(BaseModel):
    ml_prediction: MLPredictionOut
    rule_based: RuleBasedSummaryOut
    agreement: bool
    confidence: str   # "high" when both agree, "low" when they disagree


# ---------------------------------------------------------------------------
# Explain schemas
# ---------------------------------------------------------------------------

class ExplainRequest(BaseModel):
    parameters: list[ParameterInput] = Field(default_factory=list)
    age: int = Field(default=30, ge=0, le=120)
    sex: str = Field(default="male", pattern="^(male|female)$")
    symptoms: list[str] = Field(default_factory=list)
    condition: str | None = Field(
        default=None,
        description="Canonical condition name to explain. If omitted, the top predicted condition is used.",
    )


class FeatureContributionOut(BaseModel):
    feature: str
    contribution: float
    direction: str      # "increases_risk" or "decreases_risk"
    percentage: str     # e.g. "32%"


class ExplainResultOut(BaseModel):
    prediction: MLPredictionOut
    explained_condition: str
    explanations: list[FeatureContributionOut]
