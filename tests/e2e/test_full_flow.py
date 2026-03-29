"""
E2E — Full flow test: upload → z-score → risk assess.

Covers the complete happy path a frontend would exercise:
  1. Upload anemia_report.csv
  2. Run z-score analysis on the returned parameters
  3. Call risk assess with anemia symptoms
  4. Verify iron deficiency anemia appears as top result with risk > 30%
"""

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

SAMPLE_DIR = Path(__file__).parent.parent.parent / "data" / "sample_reports"


@pytest.fixture
def mock_simplify():
    from backend.core.simplifier import ParameterExplanation, SimplificationResult
    result = SimplificationResult(
        explanations=[],
        summary="Mock explanation for e2e test.",
        cached=False,
    )
    with patch("backend.api.v1.reports.simplify", new=AsyncMock(return_value=result)):
        yield


class TestFullAnемiaFlow:
    async def test_upload_parses_anemia_report(self, client, mock_simplify):
        report = (SAMPLE_DIR / "anemia_report.csv").read_bytes()
        resp = await client.post(
            "/api/v1/reports/upload",
            files={"file": ("anemia_report.csv", report, "text/csv")},
            data={"age": "28", "sex": "female"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["parameter_count"] >= 5
        assert data["anomaly_count"] >= 1

    async def test_upload_detects_low_hemoglobin(self, client, mock_simplify):
        report = (SAMPLE_DIR / "anemia_report.csv").read_bytes()
        resp = await client.post(
            "/api/v1/reports/upload",
            files={"file": ("anemia_report.csv", report, "text/csv")},
            data={"age": "28", "sex": "female"},
        )
        params = {p["name"]: p for p in resp.json()["data"]["parameters"]}
        assert "hemoglobin" in params
        assert params["hemoglobin"]["status"] == "low"

    async def test_zscore_on_anemia_params_detects_anomalies(self, client):
        payload = {
            "parameters": [
                {"name": "hemoglobin", "value": 9.5,  "unit": "g/dL"},
                {"name": "rbc",        "value": 3.2,  "unit": "M/uL"},
                {"name": "mcv",        "value": 68.0, "unit": "fL"},
                {"name": "mch",        "value": 22.0, "unit": "pg"},
                {"name": "ferritin",   "value": 6.0,  "unit": "ng/mL"},
                {"name": "iron",       "value": 35.0, "unit": "ug/dL"},
                {"name": "tibc",       "value": 420.0,"unit": "ug/dL"},
            ],
            "age": 28,
            "sex": "female",
        }
        resp = await client.post("/api/v1/analysis/zscore", json=payload)
        assert resp.status_code == 200
        summary = resp.json()["data"]["summary"]
        assert summary["anomaly_count"] >= 2

    async def test_risk_assess_flags_iron_deficiency_anemia(self, client):
        payload = {
            "parameters": [
                {"name": "hemoglobin", "value": 9.5,  "unit": "g/dL"},
                {"name": "rbc",        "value": 3.2,  "unit": "M/uL"},
                {"name": "mcv",        "value": 68.0, "unit": "fL"},
                {"name": "mch",        "value": 22.0, "unit": "pg"},
                {"name": "ferritin",   "value": 6.0,  "unit": "ng/mL"},
                {"name": "iron",       "value": 35.0, "unit": "ug/dL"},
                {"name": "tibc",       "value": 420.0,"unit": "ug/dL"},
            ],
            "age": 28,
            "sex": "female",
            "symptoms": ["fatigue", "dizziness", "pale_skin"],
        }
        resp = await client.post("/api/v1/risk/assess", json=payload)
        assert resp.status_code == 200
        conditions = resp.json()["data"]["conditions"]
        anemia = next((c for c in conditions if c["name"] == "iron_deficiency_anemia"), None)
        assert anemia is not None, "iron_deficiency_anemia not found in results"
        assert anemia["risk_percent"] >= 30

    async def test_risk_assess_anemia_is_top_condition(self, client):
        payload = {
            "parameters": [
                {"name": "hemoglobin", "value": 9.5,  "unit": "g/dL"},
                {"name": "ferritin",   "value": 6.0,  "unit": "ng/mL"},
                {"name": "iron",       "value": 35.0, "unit": "ug/dL"},
                {"name": "tibc",       "value": 420.0,"unit": "ug/dL"},
                {"name": "mcv",        "value": 68.0, "unit": "fL"},
            ],
            "age": 28,
            "sex": "female",
            "symptoms": ["fatigue", "dizziness", "pale_skin", "cold_hands_feet"],
        }
        resp = await client.post("/api/v1/risk/assess", json=payload)
        top = resp.json()["data"]["top_condition"]
        assert top == "iron_deficiency_anemia"

    async def test_full_flow_disclaimer_present_at_every_step(self, client, mock_simplify):
        report = (SAMPLE_DIR / "anemia_report.csv").read_bytes()

        # Step 1 — upload
        r1 = await client.post(
            "/api/v1/reports/upload",
            files={"file": ("anemia_report.csv", report, "text/csv")},
            data={"age": "28", "sex": "female"},
        )
        assert isinstance(r1.json().get("disclaimer"), str)

        # Step 2 — z-score
        r2 = await client.post("/api/v1/analysis/zscore", json={
            "parameters": [{"name": "hemoglobin", "value": 9.5, "unit": "g/dL"}],
            "age": 28, "sex": "female",
        })
        assert isinstance(r2.json().get("disclaimer"), str)

        # Step 3 — risk
        r3 = await client.post("/api/v1/risk/assess", json={
            "parameters": [{"name": "hemoglobin", "value": 9.5, "unit": "g/dL"}],
            "age": 28, "sex": "female",
            "symptoms": ["fatigue"],
        })
        assert isinstance(r3.json().get("disclaimer"), str)


class TestFullDiabetesFlow:
    async def test_high_glucose_triggers_immediate_attention(self, client):
        payload = {
            "parameters": [
                {"name": "glucose", "value": 280.0, "unit": "mg/dL"},
                {"name": "hba1c",   "value": 9.2,   "unit": "%"},
            ],
            "age": 45,
            "sex": "male",
            "symptoms": ["excessive_thirst", "frequent_urination", "fatigue"],
        }
        resp = await client.post("/api/v1/risk/assess", json=payload)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["requires_immediate_attention"] is True
        disclaimer = resp.json()["disclaimer"]
        assert "critical" in disclaimer.lower() or "immediately" in disclaimer.lower()

    async def test_high_glucose_diabetes_high_risk(self, client):
        payload = {
            "parameters": [
                {"name": "glucose", "value": 280.0, "unit": "mg/dL"},
                {"name": "hba1c",   "value": 9.2,   "unit": "%"},
            ],
            "age": 45,
            "sex": "male",
            "symptoms": ["excessive_thirst", "frequent_urination"],
        }
        resp = await client.post("/api/v1/risk/assess", json=payload)
        conditions = resp.json()["data"]["conditions"]
        diabetes = next((c for c in conditions if c["name"] == "type_2_diabetes"), None)
        assert diabetes is not None
        assert diabetes["risk_percent"] >= 50
