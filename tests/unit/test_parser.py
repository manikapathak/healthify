import pytest

from backend.core.parser import ParseError, BloodParameter, parse_csv, normalize_name


# ---------------------------------------------------------------------------
# normalize_name
# ---------------------------------------------------------------------------

class TestNormalizeName:
    def test_canonical_name(self):
        assert normalize_name("hemoglobin") == "hemoglobin"

    def test_alias_hb(self):
        assert normalize_name("Hb") == "hemoglobin"

    def test_alias_hgb(self):
        assert normalize_name("HGB") == "hemoglobin"

    def test_alias_glucose_fbs(self):
        assert normalize_name("FBS") == "glucose"

    def test_alias_wbc(self):
        assert normalize_name("White Blood Cells") == "wbc"

    def test_alias_hba1c(self):
        assert normalize_name("A1C") == "hba1c"

    def test_alias_ldl_cholesterol(self):
        assert normalize_name("LDL Cholesterol") == "ldl"

    def test_unknown_returns_none(self):
        assert normalize_name("xyz_unknown_param") is None

    def test_strips_whitespace(self):
        assert normalize_name("  hemoglobin  ") == "hemoglobin"


# ---------------------------------------------------------------------------
# parse_csv — multi-row format
# ---------------------------------------------------------------------------

MULTIROW_CSV = b"""Parameter,Value,Unit
Hemoglobin,14.5,g/dL
Glucose,95,mg/dL
WBC,7000,/uL
"""

MULTIROW_NO_UNIT = b"""Test Name,Result
Hemoglobin,14.5
Glucose,95
"""

class TestMultiRowParsing:
    def test_parses_parameters(self):
        result = parse_csv(MULTIROW_CSV)
        names = [p.name for p in result.parameters]
        assert "hemoglobin" in names
        assert "glucose" in names
        assert "wbc" in names

    def test_parses_values(self):
        result = parse_csv(MULTIROW_CSV)
        hb = next(p for p in result.parameters if p.name == "hemoglobin")
        assert hb.value == 14.5
        assert hb.unit == "g/dL"

    def test_preserves_raw_name(self):
        result = parse_csv(MULTIROW_CSV)
        hb = next(p for p in result.parameters if p.name == "hemoglobin")
        assert hb.raw_name == "Hemoglobin"

    def test_no_unit_column(self):
        result = parse_csv(MULTIROW_NO_UNIT)
        assert len(result.parameters) == 2
        assert result.parameters[0].unit == ""

    def test_returns_frozen_dataclass(self):
        result = parse_csv(MULTIROW_CSV)
        param = result.parameters[0]
        assert isinstance(param, BloodParameter)
        with pytest.raises(Exception):
            param.value = 999  # frozen — should raise


# ---------------------------------------------------------------------------
# parse_csv — single-row format
# ---------------------------------------------------------------------------

SINGLEROW_CSV = b"""Hemoglobin,Glucose,WBC
14.5,95,7000
"""

class TestSingleRowParsing:
    def test_parses_parameters(self):
        result = parse_csv(SINGLEROW_CSV)
        names = [p.name for p in result.parameters]
        assert "hemoglobin" in names
        assert "glucose" in names

    def test_correct_values(self):
        result = parse_csv(SINGLEROW_CSV)
        glucose = next(p for p in result.parameters if p.name == "glucose")
        assert glucose.value == 95.0


# ---------------------------------------------------------------------------
# Unrecognized parameters
# ---------------------------------------------------------------------------

UNKNOWN_PARAMS_CSV = b"""Parameter,Value,Unit
Hemoglobin,14.5,g/dL
XYZ_Unknown,99,units
"""

class TestUnrecognizedParams:
    def test_unknown_goes_to_unrecognized(self):
        result = parse_csv(UNKNOWN_PARAMS_CSV)
        assert "XYZ_Unknown" in result.unrecognized

    def test_known_still_parsed(self):
        result = parse_csv(UNKNOWN_PARAMS_CSV)
        assert any(p.name == "hemoglobin" for p in result.parameters)


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_empty_csv_raises(self):
        with pytest.raises(ParseError):
            parse_csv(b"")

    def test_headers_only_raises(self):
        with pytest.raises(ParseError):
            parse_csv(b"Parameter,Value,Unit\n")

    def test_comma_in_value(self):
        csv = b"Parameter,Value,Unit\nPlatelets,250,000,/uL\n"
        # pandas may handle this differently — should not crash
        try:
            parse_csv(csv)
        except ParseError:
            pass  # acceptable

    def test_whitespace_in_names(self):
        csv = b"Parameter,Value,Unit\n  Hemoglobin  ,14.5,g/dL\n"
        result = parse_csv(csv)
        assert any(p.name == "hemoglobin" for p in result.parameters)
