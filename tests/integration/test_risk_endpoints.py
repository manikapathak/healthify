"""
Integration tests for /api/v1/risk/* endpoints — Phase 4.

Covers:
  GET  /api/v1/risk/symptoms
  POST /api/v1/risk/assess
"""

import pytest


# ---------------------------------------------------------------------------
# GET /api/v1/risk/symptoms
# ---------------------------------------------------------------------------

class TestSymptomsEndpoint:
    async def test_returns_200(self, client):
        resp = await client.get("/api/v1/risk/symptoms")
        assert resp.status_code == 200

    async def test_success_true(self, client):
        resp = await client.get("/api/v1/risk/symptoms")
        assert resp.json()["success"] is True

    async def test_data_is_list(self, client):
        resp = await client.get("/api/v1/risk/symptoms")
        assert isinstance(resp.json()["data"], list)

    async def test_returns_at_least_10_symptoms(self, client):
        resp = await client.get("/api/v1/risk/symptoms")
        assert len(resp.json()["data"]) >= 10

    async def test_symptoms_are_strings(self, client):
        resp = await client.get("/api/v1/risk/symptoms")
        for sym in resp.json()["data"]:
            assert isinstance(sym, str)

    async def test_no_duplicate_symptoms(self, client):
        symptoms = resp = await client.get("/api/v1/risk/symptoms")
        data = resp.json()["data"]
        assert len(data) == len(set(data))


# ---------------------------------------------------------------------------
# POST /api/v1/risk/assess
# ---------------------------------------------------------------------------

ANEMIA_PARAMS = [
    {"name": "hemoglobin", "value": 9.0,  "unit": "g/dL"},
    {"name": "rbc",        "value": 3.2,  "unit": "M/uL"},
    {"name": "mcv",        "value": 65.0, "unit": "fL"},
    {"name": "mch",        "value": 19.0, "unit": "pg"},
]

NORMAL_PARAMS = [
    {"name": "hemoglobin", "value": 14.5, "unit": "g/dL"},
    {"name": "glucose",    "value": 88.0, "unit": "mg/dL"},
    {"name": "wbc",        "value": 7200, "unit": "/uL"},
]

CRITICAL_PARAMS = [
    {"name": "glucose",    "value": 280.0, "unit": "mg/dL"},
    {"name": "hemoglobin", "value": 5.0,   "unit": "g/dL"},
]


class TestRiskAssessEndpoint:
    async def test_returns_200(self, client):
        payload = {"parameters": ANEMIA_PARAMS, "age": 30, "sex": "female", "symptoms": ["fatigue"]}
        resp = await client.post("/api/v1/risk/assess", json=payload)
        assert resp.status_code == 200

    async def test_success_true(self, client):
        payload = {"parameters": ANEMIA_PARAMS, "age": 30, "sex": "female", "symptoms": ["fatigue"]}
        resp = await client.post("/api/v1/risk/assess", json=payload)
        assert resp.json()["success"] is True

    async def test_data_has_conditions(self, client):
        payload = {"parameters": ANEMIA_PARAMS, "age": 30, "sex": "female", "symptoms": ["fatigue"]}
        resp = await client.post("/api/v1/risk/assess", json=payload)
        data = resp.json()["data"]
        assert "conditions" in data
        assert isinstance(data["conditions"], list)

    async def test_data_has_required_top_level_fields(self, client):
        payload = {"parameters": ANEMIA_PARAMS, "age": 30, "sex": "female", "symptoms": []}
        resp = await client.post("/api/v1/risk/assess", json=payload)
        data = resp.json()["data"]
        assert "conditions" in data
        assert "requires_immediate_attention" in data
        assert "top_condition" in data

    async def test_each_condition_has_required_fields(self, client):
        payload = {"parameters": ANEMIA_PARAMS, "age": 30, "sex": "female", "symptoms": ["fatigue"]}
        resp = await client.post("/api/v1/risk/assess", json=payload)
        for cond in resp.json()["data"]["conditions"]:
            assert "name" in cond
            assert "display_name" in cond
            assert "risk_percent" in cond
            assert "severity" in cond
            assert "requires_doctor" in cond
            assert "message" in cond
            assert "lifestyle_tips" in cond

    async def test_conditions_sorted_by_risk_descending(self, client):
        payload = {"parameters": ANEMIA_PARAMS, "age": 30, "sex": "female", "symptoms": ["fatigue", "dizziness"]}
        resp = await client.post("/api/v1/risk/assess", json=payload)
        percents = [c["risk_percent"] for c in resp.json()["data"]["conditions"]]
        assert percents == sorted(percents, reverse=True)

    async def test_anemia_params_with_symptoms_high_risk(self, client):
        payload = {
            "parameters": ANEMIA_PARAMS,
            "age": 30,
            "sex": "female",
            "symptoms": ["fatigue", "dizziness", "pale_skin"],
        }
        resp = await client.post("/api/v1/risk/assess", json=payload)
        conditions = resp.json()["data"]["conditions"]
        anemia = next((c for c in conditions if c["name"] == "iron_deficiency_anemia"), None)
        assert anemia is not None
        assert anemia["risk_percent"] >= 30

    async def test_normal_params_no_symptoms_all_low_risk(self, client):
        payload = {"parameters": NORMAL_PARAMS, "age": 30, "sex": "male", "symptoms": []}
        resp = await client.post("/api/v1/risk/assess", json=payload)
        for cond in resp.json()["data"]["conditions"]:
            assert cond["risk_percent"] <= 20

    async def test_critical_values_trigger_immediate_attention(self, client):
        payload = {"parameters": CRITICAL_PARAMS, "age": 30, "sex": "male", "symptoms": []}
        resp = await client.post("/api/v1/risk/assess", json=payload)
        assert resp.json()["data"]["requires_immediate_attention"] is True

    async def test_critical_values_critical_disclaimer(self, client):
        payload = {"parameters": CRITICAL_PARAMS, "age": 30, "sex": "male", "symptoms": []}
        resp = await client.post("/api/v1/risk/assess", json=payload)
        disclaimer = resp.json()["disclaimer"]
        assert "critical" in disclaimer.lower() or "immediately" in disclaimer.lower() or "attention" in disclaimer.lower()

    async def test_empty_params_and_symptoms_returns_200(self, client):
        payload = {"parameters": [], "age": 30, "sex": "male", "symptoms": []}
        resp = await client.post("/api/v1/risk/assess", json=payload)
        assert resp.status_code == 200

    async def test_unknown_symptoms_ignored(self, client):
        payload = {"parameters": [], "age": 30, "sex": "male", "symptoms": ["xyz_made_up_symptom"]}
        resp = await client.post("/api/v1/risk/assess", json=payload)
        assert resp.status_code == 200

    async def test_invalid_sex_rejected(self, client):
        payload = {"parameters": [], "age": 30, "sex": "robot", "symptoms": []}
        resp = await client.post("/api/v1/risk/assess", json=payload)
        assert resp.status_code == 422

    async def test_disclaimer_always_present(self, client):
        payload = {"parameters": NORMAL_PARAMS, "age": 30, "sex": "male", "symptoms": []}
        resp = await client.post("/api/v1/risk/assess", json=payload)
        assert isinstance(resp.json().get("disclaimer"), str)
        assert len(resp.json()["disclaimer"]) > 0
