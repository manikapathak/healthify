from pydantic import BaseModel, Field


class BloodParameterOut(BaseModel):
    name: str
    raw_name: str
    value: float
    unit: str
    status: str       # low / normal / high / unknown
    is_critical: bool = False
    ref_low: float | None = None
    ref_high: float | None = None
    ref_unit: str | None = None


class UploadReportResponse(BaseModel):
    parameters: list[BloodParameterOut]
    unrecognized: list[str] = Field(default_factory=list)
    validation_errors: list[str] = Field(default_factory=list)
    simplification: str | None = None
    simplification_cached: bool = False
    parameter_count: int
    anomaly_count: int
