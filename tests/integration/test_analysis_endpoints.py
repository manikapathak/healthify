"""
Integration tests for /api/v1/analysis/* endpoints.
Covers: zscore, isolation-forest, compare
"""

import pytest


ZSCORE_URL = "/api/v1/analysis/zscore"


def body(params: list[dict], age: int = 30, sex: str = "male") -> dict:
    return {"parameters": params, "age": age, "sex": sex}


class TestZScoreEndpoint:
    async def test_returns_200(self, client):
        payload = body([{"name": "hemoglobin", "value": 14.0, "unit": "g/dL"}])
        resp = await client.post(ZSCORE_URL, json=payload)
        assert resp.status_code == 200

    async def test_success_true(self, client):
        payload = body([{"name": "hemoglobin", "value": 14.0, "unit": "g/dL"}])
        resp = await client.post(ZSCORE_URL, json=payload)
        assert resp.json()["success"] is True

    async def test_has_disclaimer(self, client):
        payload = body([{"name": "hemoglobin", "value": 14.0, "unit": "g/dL"}])
        resp = await client.post(ZSCORE_URL, json=payload)
        assert "disclaimer" in resp.json()

    async def test_normal_value_has_normal_severity(self, client):
        payload = body([{"name": "hemoglobin", "value": 14.0, "unit": "g/dL"}], sex="female")
        resp = await client.post(ZSCORE_URL, json=payload)
        scores = resp.json()["data"]["scores"]
        assert scores["hemoglobin"]["severity"] == "normal"

    async def test_low_value_flagged(self, client):
        payload = body([{"name": "hemoglobin", "value": 10.0, "unit": "g/dL"}], sex="female")
        resp = await client.post(ZSCORE_URL, json=payload)
        scores = resp.json()["data"]["scores"]
        assert scores["hemoglobin"]["status"] == "low"
        assert scores["hemoglobin"]["severity"] in ("moderate", "severe")

    async def test_high_glucose_flagged(self, client):
        payload = body([{"name": "glucose", "value": 200.0, "unit": "mg/dL"}])
        resp = await client.post(ZSCORE_URL, json=payload)
        scores = resp.json()["data"]["scores"]
        assert scores["glucose"]["status"] == "high"
        assert scores["glucose"]["severity"] in ("moderate", "severe")

    async def test_summary_anomaly_count(self, client):
        payload = body([
            {"name": "hemoglobin", "value": 14.0, "unit": "g/dL"},  # normal
            {"name": "glucose",    "value": 200.0, "unit": "mg/dL"}, # anomaly
        ], sex="male")
        resp = await client.post(ZSCORE_URL, json=payload)
        summary = resp.json()["data"]["summary"]
        assert summary["total_parameters"] == 2
        assert summary["anomaly_count"] >= 1

    async def test_unknown_parameters_skipped(self, client):
        payload = body([{"name": "xyz_totally_unknown", "value": 99.0, "unit": ""}])
        resp = await client.post(ZSCORE_URL, json=payload)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["scores"] == {}
        assert data["summary"]["total_parameters"] == 0

    async def test_multiple_parameters(self, client):
        payload = body([
            {"name": "hemoglobin",  "value": 10.0,  "unit": "g/dL"},
            {"name": "glucose",     "value": 95.0,  "unit": "mg/dL"},
            {"name": "cholesterol", "value": 240.0, "unit": "mg/dL"},
        ], sex="female")
        resp = await client.post(ZSCORE_URL, json=payload)
        data = resp.json()["data"]
        assert data["summary"]["total_parameters"] == 3

    async def test_critical_value_sets_flag(self, client):
        # Hemoglobin 5.0 < critical_low 7.0
        payload = body([{"name": "hemoglobin", "value": 5.0, "unit": "g/dL"}], sex="female")
        resp = await client.post(ZSCORE_URL, json=payload)
        summary = resp.json()["data"]["summary"]
        assert summary["has_critical"] is True

    async def test_critical_triggers_strong_disclaimer(self, client):
        payload = body([{"name": "hemoglobin", "value": 5.0, "unit": "g/dL"}], sex="female")
        resp = await client.post(ZSCORE_URL, json=payload)
        disclaimer = resp.json()["disclaimer"]
        assert "medical" in disclaimer.lower() or "doctor" in disclaimer.lower() or "attention" in disclaimer.lower()

    async def test_empty_parameters_list(self, client):
        payload = body([])
        resp = await client.post(ZSCORE_URL, json=payload)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["scores"] == {}
        assert data["summary"]["total_parameters"] == 0

    async def test_invalid_sex_rejected(self, client):
        payload = {"parameters": [], "age": 30, "sex": "robot"}
        resp = await client.post(ZSCORE_URL, json=payload)
        assert resp.status_code == 422

    async def test_age_out_of_range_rejected(self, client):
        payload = {"parameters": [], "age": 200, "sex": "male"}
        resp = await client.post(ZSCORE_URL, json=payload)
        assert resp.status_code == 422

    async def test_response_includes_ref_range(self, client):
        payload = body([{"name": "hemoglobin", "value": 14.0, "unit": "g/dL"}], sex="female")
        resp = await client.post(ZSCORE_URL, json=payload)
        score = resp.json()["data"]["scores"]["hemoglobin"]
        assert "ref_low" in score
        assert "ref_high" in score
        assert score["ref_low"] == 12.0
        assert score["ref_high"] == 16.0


# ---------------------------------------------------------------------------
# Isolation Forest endpoint
# ---------------------------------------------------------------------------

IF_URL = "/api/v1/analysis/isolation-forest"

NORMAL_CBC = [
    {"name": "hemoglobin", "value": 15.0, "unit": "g/dL"},
    {"name": "rbc",        "value": 5.0,  "unit": "M/uL"},
    {"name": "wbc",        "value": 7000, "unit": "/uL"},
    {"name": "platelets",  "value": 250000, "unit": "/uL"},
    {"name": "mcv",        "value": 88.0, "unit": "fL"},
    {"name": "mch",        "value": 30.0, "unit": "pg"},
    {"name": "mchc",       "value": 34.0, "unit": "g/dL"},
]


class TestIsolationForestEndpoint:
    async def test_returns_200(self, client):
        resp = await client.post(IF_URL, json=body(NORMAL_CBC))
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    async def test_result_has_required_fields(self, client):
        resp = await client.post(IF_URL, json=body(NORMAL_CBC))
        data = resp.json()["data"]
        assert "anomaly_score" in data
        assert "is_anomalous" in data
        assert "confidence" in data

    async def test_anomaly_score_is_float(self, client):
        resp = await client.post(IF_URL, json=body(NORMAL_CBC))
        assert isinstance(resp.json()["data"]["anomaly_score"], float)

    async def test_is_anomalous_is_bool(self, client):
        resp = await client.post(IF_URL, json=body(NORMAL_CBC))
        assert isinstance(resp.json()["data"]["is_anomalous"], bool)

    async def test_confidence_valid_value(self, client):
        resp = await client.post(IF_URL, json=body(NORMAL_CBC))
        assert resp.json()["data"]["confidence"] in ("high", "medium", "low")

    async def test_empty_params_returns_200(self, client):
        resp = await client.post(IF_URL, json=body([]))
        assert resp.status_code == 200

    async def test_disclaimer_present(self, client):
        resp = await client.post(IF_URL, json=body(NORMAL_CBC))
        assert isinstance(resp.json().get("disclaimer"), str)

    async def test_invalid_sex_rejected(self, client):
        resp = await client.post(IF_URL, json={"parameters": [], "age": 30, "sex": "robot"})
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Compare endpoint
# ---------------------------------------------------------------------------

COMPARE_URL = "/api/v1/analysis/compare"


class TestCompareEndpoint:
    async def test_returns_200(self, client):
        resp = await client.post(COMPARE_URL, json=body(NORMAL_CBC))
        assert resp.status_code == 200

    async def test_has_both_sections(self, client):
        resp = await client.post(COMPARE_URL, json=body(NORMAL_CBC))
        data = resp.json()["data"]
        assert "zscore" in data
        assert "isolation_forest" in data

    async def test_agreement_is_bool(self, client):
        resp = await client.post(COMPARE_URL, json=body(NORMAL_CBC))
        assert isinstance(resp.json()["data"]["agreement"], bool)

    async def test_zscore_section_has_scores(self, client):
        resp = await client.post(COMPARE_URL, json=body(NORMAL_CBC))
        zscore = resp.json()["data"]["zscore"]
        assert "scores" in zscore
        assert "summary" in zscore

    async def test_if_section_has_anomaly_score(self, client):
        resp = await client.post(COMPARE_URL, json=body(NORMAL_CBC))
        ifd = resp.json()["data"]["isolation_forest"]
        assert "anomaly_score" in ifd

    async def test_empty_params_does_not_crash(self, client):
        resp = await client.post(COMPARE_URL, json=body([]))
        assert resp.status_code == 200

    async def test_disclaimer_present(self, client):
        resp = await client.post(COMPARE_URL, json=body(NORMAL_CBC))
        assert isinstance(resp.json().get("disclaimer"), str)
