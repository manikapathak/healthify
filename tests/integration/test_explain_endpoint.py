"""
Integration tests for POST /api/v1/analysis/explain — Phase 6.
"""

import pytest

URL = "/api/v1/analysis/explain"

ANEMIA_PARAMS = [
    {"name": "hemoglobin",  "value": 7.5,  "unit": "g/dL"},
    {"name": "mcv",         "value": 60.0, "unit": "fL"},
    {"name": "mch",         "value": 16.0, "unit": "pg"},
    {"name": "rbc",         "value": 2.8,  "unit": "M/uL"},
    {"name": "hematocrit",  "value": 22.0, "unit": "%"},
]

NORMAL_PARAMS = [
    {"name": "hemoglobin", "value": 15.0, "unit": "g/dL"},
    {"name": "glucose",    "value": 88.0, "unit": "mg/dL"},
    {"name": "wbc",        "value": 7200, "unit": "/uL"},
]

DIABETES_PARAMS = [
    {"name": "glucose", "value": 250.0, "unit": "mg/dL"},
    {"name": "hba1c",   "value": 9.5,   "unit": "%"},
]


def body(params, age=30, sex="male", symptoms=None, condition=None):
    payload = {"parameters": params, "age": age, "sex": sex, "symptoms": symptoms or []}
    if condition:
        payload["condition"] = condition
    return payload


class TestExplainEndpoint:
    async def test_returns_200(self, client):
        resp = await client.post(URL, json=body(ANEMIA_PARAMS, sex="female"))
        assert resp.status_code == 200

    async def test_success_true(self, client):
        resp = await client.post(URL, json=body(ANEMIA_PARAMS, sex="female"))
        assert resp.json()["success"] is True

    async def test_data_has_prediction(self, client):
        resp = await client.post(URL, json=body(ANEMIA_PARAMS, sex="female"))
        assert "prediction" in resp.json()["data"]

    async def test_data_has_explanations(self, client):
        resp = await client.post(URL, json=body(ANEMIA_PARAMS, sex="female"))
        assert "explanations" in resp.json()["data"]

    async def test_explanations_is_list(self, client):
        resp = await client.post(URL, json=body(ANEMIA_PARAMS, sex="female"))
        assert isinstance(resp.json()["data"]["explanations"], list)

    async def test_at_most_5_explanations(self, client):
        resp = await client.post(URL, json=body(ANEMIA_PARAMS, sex="female"))
        assert len(resp.json()["data"]["explanations"]) <= 5

    async def test_each_explanation_has_required_fields(self, client):
        resp = await client.post(URL, json=body(ANEMIA_PARAMS, sex="female"))
        for item in resp.json()["data"]["explanations"]:
            assert "feature" in item
            assert "contribution" in item
            assert "direction" in item
            assert "percentage" in item

    async def test_direction_valid_value(self, client):
        resp = await client.post(URL, json=body(ANEMIA_PARAMS, sex="female"))
        for item in resp.json()["data"]["explanations"]:
            assert item["direction"] in ("increases_risk", "decreases_risk")

    async def test_prediction_has_top_condition_and_probability(self, client):
        resp = await client.post(URL, json=body(ANEMIA_PARAMS, sex="female"))
        pred = resp.json()["data"]["prediction"]
        assert "top_condition" in pred
        assert "top_probability" in pred

    async def test_condition_override_respected(self, client):
        resp = await client.post(URL, json=body(ANEMIA_PARAMS, condition="iron_deficiency_anemia"))
        data = resp.json()["data"]
        assert data["explained_condition"] == "iron_deficiency_anemia"

    async def test_disclaimer_present(self, client):
        resp = await client.post(URL, json=body(NORMAL_PARAMS))
        assert isinstance(resp.json().get("disclaimer"), str)

    async def test_empty_params_returns_200(self, client):
        resp = await client.post(URL, json=body([]))
        assert resp.status_code == 200

    async def test_invalid_sex_rejected(self, client):
        resp = await client.post(URL, json={
            "parameters": [], "age": 30, "sex": "robot", "symptoms": []
        })
        assert resp.status_code == 422

    async def test_anemia_top_feature_is_cbc_marker(self, client):
        resp = await client.post(URL, json=body(ANEMIA_PARAMS, sex="female",
                                                condition="iron_deficiency_anemia"))
        explanations = resp.json()["data"]["explanations"]
        if explanations:
            cbc = {"hemoglobin", "mcv", "mch", "mchc", "rbc", "hematocrit"}
            assert explanations[0]["feature"] in cbc

    async def test_diabetes_top_feature_is_glucose_or_hba1c(self, client):
        resp = await client.post(URL, json=body(DIABETES_PARAMS,
                                                condition="type_2_diabetes"))
        explanations = resp.json()["data"]["explanations"]
        if explanations:
            assert explanations[0]["feature"] in {"glucose", "hba1c"}
