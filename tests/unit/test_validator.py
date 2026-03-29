import pytest

from backend.core.parser import BloodParameter
from backend.core.validator import validate


def make_param(name: str, value: float, unit: str = "") -> BloodParameter:
    return BloodParameter(name=name, raw_name=name, value=value, unit=unit)


class TestValidatorHappyPath:
    def test_normal_hemoglobin_passes(self):
        result = validate([make_param("hemoglobin", 14.5)])
        assert not result.has_errors
        assert len(result.valid) == 1

    def test_normal_glucose_passes(self):
        result = validate([make_param("glucose", 90.0)])
        assert not result.has_errors

    def test_multiple_valid_params(self):
        params = [
            make_param("hemoglobin", 14.5),
            make_param("glucose", 90.0),
            make_param("wbc", 7000),
        ]
        result = validate(params)
        assert not result.has_errors
        assert len(result.valid) == 3


class TestValidatorRejectsImpossibleValues:
    def test_hemoglobin_too_high(self):
        result = validate([make_param("hemoglobin", 500.0)])
        assert result.has_errors
        assert len(result.errors) == 1
        assert "hemoglobin" in result.errors[0].parameter

    def test_negative_value(self):
        result = validate([make_param("glucose", -1.0)])
        assert result.has_errors

    def test_wbc_astronomically_high(self):
        result = validate([make_param("wbc", 99_000_000)])
        assert result.has_errors

    def test_invalid_goes_to_errors_valid_stays_in_valid(self):
        params = [
            make_param("hemoglobin", 14.5),   # valid
            make_param("glucose", 99999.0),    # invalid
        ]
        result = validate(params)
        assert len(result.valid) == 1
        assert len(result.errors) == 1
        assert result.valid[0].name == "hemoglobin"


class TestValidatorBoundaryValues:
    def test_exact_max_is_valid(self):
        # hemoglobin max is 25.0
        result = validate([make_param("hemoglobin", 25.0)])
        assert not result.has_errors

    def test_just_above_max_is_invalid(self):
        result = validate([make_param("hemoglobin", 25.01)])
        assert result.has_errors

    def test_zero_is_valid(self):
        result = validate([make_param("hemoglobin", 0.0)])
        assert not result.has_errors


class TestValidatorUnknownParams:
    def test_unknown_parameter_passes_through(self):
        # Unknown params have no limits defined — should pass
        result = validate([make_param("some_unknown_test", 42.0)])
        assert not result.has_errors
        assert len(result.valid) == 1
