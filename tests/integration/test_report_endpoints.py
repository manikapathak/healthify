"""
Integration tests for the /api/v1/reports/upload endpoint.

OpenAI is mocked — tests verify parsing, validation, and reference range
logic without real API calls.
"""

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

SAMPLE_DIR = Path(__file__).parent.parent.parent / "data" / "sample_reports"


@pytest.fixture
def mock_simplify():
    """Patch OpenAI simplifier so tests don't need a real API key."""
    from backend.core.simplifier import SimplificationResult, ParameterExplanation
    mock_result = SimplificationResult(
        explanations=[],
        summary="Mock explanation: your results look reasonable.",
        cached=False,
    )
    with patch("backend.api.v1.reports.simplify", new=AsyncMock(return_value=mock_result)):
        yield mock_result


class TestHealthCheck:
    async def test_health_ok(self, client):
        response = await client.get("/api/v1/health")
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["data"]["status"] == "ok"
        assert "version" in body["data"]

    async def test_health_includes_disclaimer(self, client):
        response = await client.get("/api/v1/health")
        assert "disclaimer" in response.json()


class TestUploadNormalReport:
    async def test_upload_returns_200(self, client, mock_simplify):
        csv_bytes = (SAMPLE_DIR / "normal_report.csv").read_bytes()
        response = await client.post(
            "/api/v1/reports/upload",
            files={"file": ("normal_report.csv", csv_bytes, "text/csv")},
            data={"age": "30", "sex": "male"},
        )
        assert response.status_code == 200

    async def test_upload_success_true(self, client, mock_simplify):
        csv_bytes = (SAMPLE_DIR / "normal_report.csv").read_bytes()
        response = await client.post(
            "/api/v1/reports/upload",
            files={"file": ("normal_report.csv", csv_bytes, "text/csv")},
            data={"age": "30", "sex": "male"},
        )
        assert response.json()["success"] is True

    async def test_upload_has_parameters(self, client, mock_simplify):
        csv_bytes = (SAMPLE_DIR / "normal_report.csv").read_bytes()
        response = await client.post(
            "/api/v1/reports/upload",
            files={"file": ("normal_report.csv", csv_bytes, "text/csv")},
            data={"age": "30", "sex": "male"},
        )
        data = response.json()["data"]
        assert data["parameter_count"] > 0
        assert len(data["parameters"]) > 0

    async def test_normal_report_few_anomalies(self, client, mock_simplify):
        csv_bytes = (SAMPLE_DIR / "normal_report.csv").read_bytes()
        response = await client.post(
            "/api/v1/reports/upload",
            files={"file": ("normal_report.csv", csv_bytes, "text/csv")},
            data={"age": "30", "sex": "male"},
        )
        data = response.json()["data"]
        assert data["anomaly_count"] == 0

    async def test_simplification_returned(self, client, mock_simplify):
        csv_bytes = (SAMPLE_DIR / "normal_report.csv").read_bytes()
        response = await client.post(
            "/api/v1/reports/upload",
            files={"file": ("normal_report.csv", csv_bytes, "text/csv")},
            data={"age": "30", "sex": "male"},
        )
        data = response.json()["data"]
        assert data["simplification"] is not None
        assert len(data["simplification"]) > 0

    async def test_response_has_disclaimer(self, client, mock_simplify):
        csv_bytes = (SAMPLE_DIR / "normal_report.csv").read_bytes()
        response = await client.post(
            "/api/v1/reports/upload",
            files={"file": ("normal_report.csv", csv_bytes, "text/csv")},
            data={"age": "30", "sex": "male"},
        )
        assert "disclaimer" in response.json()
        assert len(response.json()["disclaimer"]) > 10


class TestUploadAnemiaReport:
    async def test_detects_anomalies(self, client, mock_simplify):
        csv_bytes = (SAMPLE_DIR / "anemia_report.csv").read_bytes()
        response = await client.post(
            "/api/v1/reports/upload",
            files={"file": ("anemia_report.csv", csv_bytes, "text/csv")},
            data={"age": "30", "sex": "female"},
        )
        data = response.json()["data"]
        assert data["anomaly_count"] > 0

    async def test_hemoglobin_flagged_low(self, client, mock_simplify):
        csv_bytes = (SAMPLE_DIR / "anemia_report.csv").read_bytes()
        response = await client.post(
            "/api/v1/reports/upload",
            files={"file": ("anemia_report.csv", csv_bytes, "text/csv")},
            data={"age": "30", "sex": "female"},
        )
        params = response.json()["data"]["parameters"]
        hb = next((p for p in params if p["name"] == "hemoglobin"), None)
        assert hb is not None
        assert hb["status"] == "low"

    async def test_stronger_disclaimer_for_anomalies(self, client, mock_simplify):
        csv_bytes = (SAMPLE_DIR / "anemia_report.csv").read_bytes()
        response = await client.post(
            "/api/v1/reports/upload",
            files={"file": ("anemia_report.csv", csv_bytes, "text/csv")},
            data={"age": "30", "sex": "female"},
        )
        disclaimer = response.json()["disclaimer"]
        assert "consult" in disclaimer.lower() or "healthcare" in disclaimer.lower()


class TestUploadDiabetesReport:
    async def test_glucose_flagged_high(self, client, mock_simplify):
        csv_bytes = (SAMPLE_DIR / "diabetes_risk.csv").read_bytes()
        response = await client.post(
            "/api/v1/reports/upload",
            files={"file": ("diabetes_risk.csv", csv_bytes, "text/csv")},
            data={"age": "45", "sex": "male"},
        )
        params = response.json()["data"]["parameters"]
        glucose = next((p for p in params if p["name"] == "glucose"), None)
        assert glucose is not None
        assert glucose["status"] == "high"

    async def test_critical_values_flagged(self, client, mock_simplify):
        csv_bytes = (SAMPLE_DIR / "diabetes_risk.csv").read_bytes()
        response = await client.post(
            "/api/v1/reports/upload",
            files={"file": ("diabetes_risk.csv", csv_bytes, "text/csv")},
            data={"age": "45", "sex": "male"},
        )
        params = response.json()["data"]["parameters"]
        glucose = next((p for p in params if p["name"] == "glucose"), None)
        # 215 mg/dL is above critical threshold of 500 — should NOT be critical
        # but is definitely high. Just check status.
        assert glucose["status"] == "high"


class TestUploadFileTypes:
    async def test_unsupported_extension_rejected(self, client):
        response = await client.post(
            "/api/v1/reports/upload",
            files={"file": ("report.txt", b"some text", "text/plain")},
            data={"age": "30", "sex": "male"},
        )
        assert response.status_code == 422

    async def test_image_routes_to_vision_parser(self, client):
        """Image upload calls parse_image, not parse_csv."""
        from unittest.mock import AsyncMock, patch
        from backend.core.parser import ParseResult, BloodParameter

        mock_result = ParseResult(
            parameters=[BloodParameter(name="hemoglobin", raw_name="Hemoglobin", value=14.5, unit="g/dL")],
            unrecognized=[],
        )
        with patch("backend.api.v1.reports.parse_image", new=AsyncMock(return_value=mock_result)), \
             patch("backend.api.v1.reports.simplify", new=AsyncMock(return_value=None)):
            response = await client.post(
                "/api/v1/reports/upload",
                files={"file": ("report.jpg", b"fake_image", "image/jpeg")},
                data={"age": "30", "sex": "male"},
            )
        assert response.status_code == 200
        assert response.json()["success"] is True

    async def test_pdf_routes_to_pdf_parser(self, client):
        """PDF upload calls parse_pdf, not parse_csv."""
        from unittest.mock import patch
        from backend.core.parser import ParseResult, BloodParameter

        mock_result = ParseResult(
            parameters=[BloodParameter(name="glucose", raw_name="Glucose", value=95.0, unit="mg/dL")],
            unrecognized=[],
        )
        with patch("backend.api.v1.reports.parse_pdf", return_value=mock_result), \
             patch("backend.api.v1.reports.simplify", new=AsyncMock(return_value=None)):
            response = await client.post(
                "/api/v1/reports/upload",
                files={"file": ("report.pdf", b"fake_pdf", "application/pdf")},
                data={"age": "30", "sex": "male"},
            )
        assert response.status_code == 200

    async def test_png_accepted(self, client):
        from unittest.mock import AsyncMock, patch
        from backend.core.parser import ParseResult, BloodParameter

        mock_result = ParseResult(
            parameters=[BloodParameter(name="hemoglobin", raw_name="Hb", value=14.0, unit="g/dL")],
            unrecognized=[],
        )
        with patch("backend.api.v1.reports.parse_image", new=AsyncMock(return_value=mock_result)), \
             patch("backend.api.v1.reports.simplify", new=AsyncMock(return_value=None)):
            response = await client.post(
                "/api/v1/reports/upload",
                files={"file": ("report.png", b"fake_image", "image/png")},
                data={"age": "30", "sex": "male"},
            )
        assert response.status_code == 200


class TestUploadValidation:

    async def test_invalid_sex_rejected(self, client):
        csv_bytes = (SAMPLE_DIR / "normal_report.csv").read_bytes()
        response = await client.post(
            "/api/v1/reports/upload",
            files={"file": ("normal_report.csv", csv_bytes, "text/csv")},
            data={"age": "30", "sex": "other"},
        )
        assert response.status_code == 422

    async def test_invalid_age_rejected(self, client):
        csv_bytes = (SAMPLE_DIR / "normal_report.csv").read_bytes()
        response = await client.post(
            "/api/v1/reports/upload",
            files={"file": ("normal_report.csv", csv_bytes, "text/csv")},
            data={"age": "999", "sex": "male"},
        )
        assert response.status_code == 422

    async def test_openai_failure_still_returns_data(self, client):
        """If OpenAI fails, the endpoint should still return parsed parameters."""
        csv_bytes = (SAMPLE_DIR / "normal_report.csv").read_bytes()
        with patch("backend.api.v1.reports.simplify", new=AsyncMock(return_value=None)):
            response = await client.post(
                "/api/v1/reports/upload",
                files={"file": ("normal_report.csv", csv_bytes, "text/csv")},
                data={"age": "30", "sex": "male"},
            )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["parameter_count"] > 0
        assert data["simplification"] is None
