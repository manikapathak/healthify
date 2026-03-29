import pytest

from backend.ml.reference_ranges import (
    AgeGroup,
    age_sex_to_group,
    get_range,
    list_parameters,
)


class TestAgeGroupMapping:
    def test_child(self):
        assert age_sex_to_group(10, "male") == AgeGroup.CHILD

    def test_adult_male(self):
        assert age_sex_to_group(35, "male") == AgeGroup.ADULT_MALE

    def test_adult_female(self):
        assert age_sex_to_group(35, "female") == AgeGroup.ADULT_FEMALE

    def test_elderly(self):
        assert age_sex_to_group(70, "male") == AgeGroup.ELDERLY

    def test_boundary_18_male(self):
        assert age_sex_to_group(18, "male") == AgeGroup.ADULT_MALE

    def test_boundary_65_female(self):
        assert age_sex_to_group(65, "female") == AgeGroup.ELDERLY

    def test_sex_case_insensitive(self):
        assert age_sex_to_group(30, "MALE") == AgeGroup.ADULT_MALE
        assert age_sex_to_group(30, "Female") == AgeGroup.ADULT_FEMALE


class TestGetRange:
    def test_hemoglobin_adult_male(self):
        ref = get_range("hemoglobin", age=30, sex="male")
        assert ref is not None
        assert ref.low == 13.5
        assert ref.high == 17.5
        assert ref.unit == "g/dL"

    def test_hemoglobin_adult_female(self):
        ref = get_range("hemoglobin", age=30, sex="female")
        assert ref is not None
        assert ref.low == 12.0
        assert ref.high == 16.0

    def test_hemoglobin_child(self):
        ref = get_range("hemoglobin", age=10, sex="male")
        assert ref is not None
        assert ref.low == 11.0

    def test_glucose_range(self):
        ref = get_range("glucose", age=30, sex="male")
        assert ref is not None
        assert ref.low == 70.0
        assert ref.high == 99.0

    def test_critical_values(self):
        ref = get_range("hemoglobin", age=30, sex="male")
        assert ref.critical_low == 7.0
        assert ref.critical_high == 20.0

    def test_unknown_parameter_returns_none(self):
        ref = get_range("xyz_not_a_real_param", age=30, sex="male")
        assert ref is None

    def test_tsh_range(self):
        ref = get_range("tsh", age=30, sex="male")
        assert ref is not None
        assert ref.low == 0.4
        assert ref.high == 4.0


class TestRangeResultClassify:
    def test_classify_normal(self):
        ref = get_range("hemoglobin", age=30, sex="male")
        assert ref.classify(15.0) == "normal"

    def test_classify_low(self):
        ref = get_range("hemoglobin", age=30, sex="male")
        assert ref.classify(10.0) == "low"

    def test_classify_high(self):
        ref = get_range("hemoglobin", age=30, sex="male")
        assert ref.classify(19.0) == "high"

    def test_is_critical_low(self):
        ref = get_range("hemoglobin", age=30, sex="male")
        assert ref.is_critical(5.0) is True   # below critical_low=7.0

    def test_is_critical_high(self):
        ref = get_range("hemoglobin", age=30, sex="male")
        assert ref.is_critical(22.0) is True  # above critical_high=20.0

    def test_not_critical_normal(self):
        ref = get_range("hemoglobin", age=30, sex="male")
        assert ref.is_critical(14.0) is False


class TestListParameters:
    def test_returns_list(self):
        params = list_parameters()
        assert isinstance(params, list)
        assert len(params) >= 20

    def test_contains_common_params(self):
        params = list_parameters()
        for expected in ["hemoglobin", "glucose", "cholesterol", "tsh", "ferritin"]:
            assert expected in params
