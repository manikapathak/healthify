from pydantic import BaseModel, Field

from backend.api.schemas.analysis import ParameterInput


class RiskAssessRequest(BaseModel):
    parameters: list[ParameterInput] = Field(default_factory=list)
    age: int = Field(default=30, ge=0, le=120)
    sex: str = Field(default="male", pattern="^(male|female)$")
    symptoms: list[str] = Field(default_factory=list)


class ConditionResultOut(BaseModel):
    name: str
    display_name: str
    risk_percent: int
    severity: str
    requires_doctor: bool
    message: str
    lifestyle_tips: list[str]


class RiskResultOut(BaseModel):
    conditions: list[ConditionResultOut]
    requires_immediate_attention: bool
    top_condition: str | None
