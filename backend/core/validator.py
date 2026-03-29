"""
Physical-limit validation for blood parameters.

These are hard biological limits — values outside these ranges are physically
impossible and indicate a data entry error or corrupt CSV.
"""

from dataclasses import dataclass

from backend.core.parser import BloodParameter

# canonical_name → (absolute_min, absolute_max, unit_hint)
_PHYSICAL_LIMITS: dict[str, tuple[float, float, str]] = {
    "hemoglobin":       (0.0,  25.0,    "g/dL"),
    "rbc":              (0.0,  10.0,    "million/uL"),
    "wbc":              (0.0,  500_000, "/uL"),
    "platelets":        (0.0,  2_000_000, "/uL"),
    "hematocrit":       (0.0,  100.0,   "%"),
    "mcv":              (0.0,  200.0,   "fL"),
    "mch":              (0.0,  60.0,    "pg"),
    "mchc":             (0.0,  50.0,    "g/dL"),
    "glucose":          (0.0,  1_000.0, "mg/dL"),
    "hba1c":            (0.0,  20.0,    "%"),
    "cholesterol":      (0.0,  1_000.0, "mg/dL"),
    "ldl":              (0.0,  800.0,   "mg/dL"),
    "hdl":              (0.0,  200.0,   "mg/dL"),
    "triglycerides":    (0.0,  5_000.0, "mg/dL"),
    "creatinine":       (0.0,  50.0,    "mg/dL"),
    "bun":              (0.0,  300.0,   "mg/dL"),
    "uric_acid":        (0.0,  30.0,    "mg/dL"),
    "alt":              (0.0,  10_000.0, "U/L"),
    "ast":              (0.0,  10_000.0, "U/L"),
    "alp":              (0.0,  5_000.0,  "U/L"),
    "bilirubin_total":  (0.0,  50.0,    "mg/dL"),
    "bilirubin_direct": (0.0,  30.0,    "mg/dL"),
    "albumin":          (0.0,  10.0,    "g/dL"),
    "protein_total":    (0.0,  20.0,    "g/dL"),
    "tsh":              (0.0,  200.0,   "mIU/L"),
    "t3":               (0.0,  1_000.0, "ng/dL"),
    "t4":               (0.0,  30.0,    "ug/dL"),
    "ferritin":         (0.0,  10_000.0, "ng/mL"),
    "iron":             (0.0,  500.0,   "ug/dL"),
    "tibc":             (0.0,  1_000.0, "ug/dL"),
    "vitamin_b12":      (0.0,  10_000.0, "pg/mL"),
    "vitamin_d":        (0.0,  400.0,   "ng/mL"),
    "sodium":           (0.0,  200.0,   "mEq/L"),
    "potassium":        (0.0,  15.0,    "mEq/L"),
    "calcium":          (0.0,  20.0,    "mg/dL"),
    "phosphorus":       (0.0,  20.0,    "mg/dL"),
    "magnesium":        (0.0,  10.0,    "mg/dL"),
    "chloride":         (0.0,  200.0,   "mEq/L"),
    "bicarbonate":      (0.0,  60.0,    "mEq/L"),
}


@dataclass(frozen=True)
class ValidationError:
    parameter: str
    value: float
    message: str


@dataclass(frozen=True)
class ValidationResult:
    valid: list[BloodParameter]
    errors: list[ValidationError]

    @property
    def has_errors(self) -> bool:
        return len(self.errors) > 0


def validate(parameters: list[BloodParameter]) -> ValidationResult:
    """
    Validate blood parameters against physical limits.
    Returns a ValidationResult separating valid params from those with errors.
    """
    valid: list[BloodParameter] = []
    errors: list[ValidationError] = []

    for param in parameters:
        limits = _PHYSICAL_LIMITS.get(param.name)

        if limits is None:
            # No limits defined — accept the value as-is
            valid.append(param)
            continue

        min_val, max_val, unit_hint = limits

        if param.value < min_val or param.value > max_val:
            errors.append(ValidationError(
                parameter=param.name,
                value=param.value,
                message=(
                    f"{param.name} value {param.value} is outside the physically "
                    f"possible range [{min_val}, {max_val}] {unit_hint}. "
                    "Please check the uploaded file."
                ),
            ))
        else:
            valid.append(param)

    return ValidationResult(valid=valid, errors=errors)
