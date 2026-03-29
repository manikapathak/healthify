"""
Reference range lookup for blood parameters.

Usage:
    from backend.ml.reference_ranges import get_range, RangeResult, AgeGroup

    result = get_range("hemoglobin", age=35, sex="male")
    print(result.low, result.high, result.is_critical_low(10.0))
"""

import json
from dataclasses import dataclass
from enum import Enum
from functools import lru_cache
from pathlib import Path

_DATA_FILE = Path(__file__).parent.parent.parent / "data" / "reference_ranges.json"


class AgeGroup(str, Enum):
    CHILD = "child"          # < 18
    ADULT_MALE = "adult_male"
    ADULT_FEMALE = "adult_female"
    ELDERLY = "elderly"      # >= 65


def age_sex_to_group(age: int, sex: str) -> AgeGroup:
    """Convert age + sex to an AgeGroup key."""
    sex_lower = sex.strip().lower()
    if age < 18:
        return AgeGroup.CHILD
    if age >= 65:
        return AgeGroup.ELDERLY
    if sex_lower in ("male", "m"):
        return AgeGroup.ADULT_MALE
    return AgeGroup.ADULT_FEMALE


@dataclass(frozen=True)
class RangeResult:
    parameter: str
    low: float
    high: float
    unit: str
    source: str
    critical_low: float
    critical_high: float

    def classify(self, value: float) -> str:
        """Return 'low', 'normal', or 'high'."""
        if value < self.low:
            return "low"
        if value > self.high:
            return "high"
        return "normal"

    def is_critical(self, value: float) -> bool:
        return value < self.critical_low or value > self.critical_high


@lru_cache(maxsize=1)
def _load_data() -> dict:
    with _DATA_FILE.open() as f:
        return json.load(f)


def get_range(parameter: str, age: int = 30, sex: str = "male") -> RangeResult | None:
    """
    Return reference range for a parameter given age and sex.
    Returns None if the parameter is not in the database.
    """
    data = _load_data()
    entry = data.get(parameter)
    if entry is None:
        return None

    group = age_sex_to_group(age, sex)
    ranges = entry.get("ranges", {})

    # Fallback chain: exact group → adult_male → adult_female → first available
    group_range = (
        ranges.get(group.value)
        or ranges.get(AgeGroup.ADULT_MALE.value)
        or ranges.get(AgeGroup.ADULT_FEMALE.value)
        or next(iter(ranges.values()), None)
    )

    if group_range is None:
        return None

    return RangeResult(
        parameter=parameter,
        low=float(group_range["low"]),
        high=float(group_range["high"]),
        unit=entry.get("unit", ""),
        source=entry.get("source", ""),
        critical_low=float(entry.get("critical_low", group_range["low"] * 0.5)),
        critical_high=float(entry.get("critical_high", group_range["high"] * 2.0)),
    )


def list_parameters() -> list[str]:
    """Return all parameter names in the reference ranges database."""
    return list(_load_data().keys())
