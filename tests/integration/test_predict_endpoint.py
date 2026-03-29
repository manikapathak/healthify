"""
Integration tests for POST /api/v1/analysis/predict — Phase 5.
"""

import pytest


NORMAL_CBC = [
    {"name": "hemoglobin", "value": 15.0, "unit": "g/dL"},
    {"name": "rbc",        "value": 5.0,  "unit": "M/uL"},
    {"name": "wbc",        "value": 7000, "unit": "/uL"},
    {"name": "platelets",  "value": 250000, "unit": "/uL"},
    {"name": "mcv",        "value": 88.0, "unit": "fL"},
    {"name": "mch",        "value": 30.0, "unit": "pg"},
    {"name": "mchc",       "value": 34.0, "unit": "g/dL"},
    {"name": "hematocrit", "value": 45.0, "unit": "%"},
]

ANEMIA_CBC = [
    {"name": "hemoglobin",  "value": 8.0,  "unit": "g/dL"},
    {"name": "mcv",         "value": 62.0, "unit": "fL"},
    {"name": "mch",         "value": 17.0, "unit": "pg"},
    {"name": "mchc",        "value": 28.0, "unit": "g/dL"},
    {"name": "rbc",         "value": 3.0,  "unit": "M/uL"},
    {"name": "hematocrit",  "value": 25.0, "unit": "%"},
]

DIABETES_PARAMS = [
    {"name": "glucose", "value": 240.0, "unit": "mg/dL"},
    {"name": "hba1c",   "value": 9.0,   "unit": "%"},
]

URL = "/api/v1/analysis/predict"


def body(params, age=30, sex="male", symptoms=None):
    return {"parameters": params, "age": age, "sex": sex, "symptoms": symptoms or []}


class TestPredictEndpoint:
    async def test_returns_200(self, client):
        resp = await client.post(URL, json=body(NORMAL_CBC))
        assert resp.status_code == 200

    async def test_success_true(self, client):
        resp = await client.post(URL, json=body(NORMAL_CBC))
        assert resp.json()["success"] is True

    async def test_data_has_ml_prediction(self, client):
        resp = await client.post(URL, json=body(NORMAL_CBC))
        assert "ml_prediction" in resp.json()["data"]

    async def test_data_has_rule_based(self, client):
        resp = await client.post(URL, json=body(NORMAL_CBC))
        assert "rule_based" in resp.json()["data"]

    async def test_data_has_agreement_and_confidence(self, client):
        resp = await client.post(URL, json=body(NORMAL_CBC))
        data = resp.json()["data"]
        assert "agreement" in data
        assert "confidence" in data

    async def test_ml_prediction_has_required_fields(self, client):
        resp = await client.post(URL, json=body(NORMAL_CBC))
        ml = resp.json()["data"]["ml_prediction"]
        assert "top_condition" in ml
        assert "top_probability" in ml
        assert "probabilities" in ml

    async def test_probabilities_is_list(self, client):
        resp = await client.post(URL, json=body(NORMAL_CBC))
        probs = resp.json()["data"]["ml_prediction"]["probabilities"]
        assert isinstance(probs, list)
        assert len(probs) > 0

    async def test_each_probability_has_required_fields(self, client):
        resp = await client.post(URL, json=body(NORMAL_CBC))
        for p in resp.json()["data"]["ml_prediction"]["probabilities"]:
            assert "condition" in p
            assert "probability" in p
            assert "display_name" in p

    async def test_probabilities_sorted_descending(self, client):
        resp = await client.post(URL, json=body(NORMAL_CBC))
        probs = [p["probability"] for p in resp.json()["data"]["ml_prediction"]["probabilities"]]
        assert probs == sorted(probs, reverse=True)

    async def test_confidence_valid_value(self, client):
        resp = await client.post(URL, json=body(NORMAL_CBC))
        assert resp.json()["data"]["confidence"] in ("high", "low")

    async def test_agreement_is_bool(self, client):
        resp = await client.post(URL, json=body(NORMAL_CBC))
        assert isinstance(resp.json()["data"]["agreement"], bool)

    async def test_rule_based_has_top_condition_and_risk(self, client):
        resp = await client.post(URL, json=body(NORMAL_CBC))
        rb = resp.json()["data"]["rule_based"]
        assert "top_condition" in rb
        assert "risk_percent" in rb

    async def test_disclaimer_present(self, client):
        resp = await client.post(URL, json=body(NORMAL_CBC))
        assert isinstance(resp.json().get("disclaimer"), str)

    async def test_empty_params_returns_200(self, client):
        resp = await client.post(URL, json=body([]))
        assert resp.status_code == 200

    async def test_invalid_sex_rejected(self, client):
        resp = await client.post(URL, json={"parameters": [], "age": 30, "sex": "robot", "symptoms": []})
        assert resp.status_code == 422

    async def test_normal_cbc_healthy_in_top3(self, client):
        resp = await client.post(URL, json=body(NORMAL_CBC, sex="male"))
        probs = resp.json()["data"]["ml_prediction"]["probabilities"]
        top3 = [p["condition"] for p in probs[:3]]
        assert "healthy" in top3

    async def test_anemia_pattern_returns_anemia_in_top3(self, client):
        resp = await client.post(URL, json=body(ANEMIA_CBC, sex="female"))
        probs = resp.json()["data"]["ml_prediction"]["probabilities"]
        top3 = {p["condition"] for p in probs[:3]}
        anemia_conditions = {
            "iron_deficiency_anemia", "normocytic_hypochromic_anemia",
            "normocytic_normochromic_anemia", "microcytic_anemia", "macrocytic_anemia",
        }
        assert top3 & anemia_conditions

    async def test_diabetes_params_returns_diabetes_in_top3(self, client):
        resp = await client.post(URL, json=body(DIABETES_PARAMS))
        probs = resp.json()["data"]["ml_prediction"]["probabilities"]
        top3 = [p["condition"] for p in probs[:3]]
        assert "type_2_diabetes" in top3
