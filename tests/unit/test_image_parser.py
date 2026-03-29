"""
Tests for image_parser.py.

OpenAI Vision is always mocked — these tests verify:
  - JSON extraction from model responses
  - Parameter normalization
  - Error handling (empty image, bad JSON, empty response, API errors)
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.core.image_parser import (
    ImageParseError,
    _build_parameters,
    _extract_json_from_response,
    parse_image,
)


# ---------------------------------------------------------------------------
# _extract_json_from_response
# ---------------------------------------------------------------------------

class TestExtractJsonFromResponse:
    def test_clean_json_array(self):
        text = '[{"name": "Hemoglobin", "value": 14.5, "unit": "g/dL"}]'
        result = _extract_json_from_response(text)
        assert len(result) == 1
        assert result[0]["name"] == "Hemoglobin"

    def test_strips_markdown_code_fence(self):
        text = '```json\n[{"name": "Glucose", "value": 95, "unit": "mg/dL"}]\n```'
        result = _extract_json_from_response(text)
        assert result[0]["value"] == 95

    def test_strips_plain_code_fence(self):
        text = '```\n[{"name": "WBC", "value": 7000, "unit": "/uL"}]\n```'
        result = _extract_json_from_response(text)
        assert result[0]["name"] == "WBC"

    def test_empty_array(self):
        result = _extract_json_from_response("[]")
        assert result == []

    def test_multiple_items(self):
        text = '[{"name": "Hb", "value": 14.5, "unit": "g/dL"}, {"name": "RBC", "value": 4.8, "unit": "million/uL"}]'
        result = _extract_json_from_response(text)
        assert len(result) == 2

    def test_invalid_json_raises(self):
        with pytest.raises(ImageParseError, match="invalid JSON"):
            _extract_json_from_response("not json at all")

    def test_json_object_raises(self):
        with pytest.raises(ImageParseError, match="Expected a JSON array"):
            _extract_json_from_response('{"name": "Hb"}')


# ---------------------------------------------------------------------------
# _build_parameters
# ---------------------------------------------------------------------------

class TestBuildParameters:
    def test_recognized_parameter(self):
        items = [{"name": "Hemoglobin", "value": 14.5, "unit": "g/dL"}]
        result = _build_parameters(items)
        assert len(result.parameters) == 1
        assert result.parameters[0].name == "hemoglobin"
        assert result.parameters[0].value == 14.5

    def test_alias_recognition(self):
        items = [{"name": "Hb", "value": 14.5, "unit": "g/dL"}]
        result = _build_parameters(items)
        assert result.parameters[0].name == "hemoglobin"

    def test_unrecognized_goes_to_unrecognized(self):
        items = [{"name": "XYZ_Unknown_Test", "value": 99, "unit": ""}]
        result = _build_parameters(items)
        assert len(result.parameters) == 0
        assert "XYZ_Unknown_Test" in result.unrecognized

    def test_non_numeric_value_goes_to_unrecognized(self):
        items = [{"name": "Hemoglobin", "value": "not_a_number", "unit": "g/dL"}]
        result = _build_parameters(items)
        assert len(result.parameters) == 0
        assert "Hemoglobin" in result.unrecognized

    def test_empty_name_skipped(self):
        items = [{"name": "", "value": 14.5, "unit": "g/dL"}]
        result = _build_parameters(items)
        assert len(result.parameters) == 0
        assert len(result.unrecognized) == 0

    def test_multiple_mixed_items(self):
        items = [
            {"name": "Hemoglobin", "value": 14.5, "unit": "g/dL"},
            {"name": "Unknown_Test", "value": 99, "unit": ""},
            {"name": "Glucose", "value": 95, "unit": "mg/dL"},
        ]
        result = _build_parameters(items)
        assert len(result.parameters) == 2
        assert len(result.unrecognized) == 1


# ---------------------------------------------------------------------------
# parse_image (integration with mocked OpenAI)
# ---------------------------------------------------------------------------

MOCK_VISION_RESPONSE = '[{"name": "Hemoglobin", "value": 14.5, "unit": "g/dL"}, {"name": "Glucose", "value": 95, "unit": "mg/dL"}]'


def _make_mock_response(content: str):
    msg = MagicMock()
    msg.content = content
    choice = MagicMock()
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]
    return resp


class TestParseImage:
    async def test_successful_extraction(self):
        mock_resp = _make_mock_response(MOCK_VISION_RESPONSE)
        with patch("backend.core.image_parser.AsyncOpenAI") as MockClient:
            instance = MockClient.return_value
            instance.chat.completions.create = AsyncMock(return_value=mock_resp)
            result = await parse_image(b"fake_image_bytes", "image/jpeg")

        assert len(result.parameters) == 2
        names = [p.name for p in result.parameters]
        assert "hemoglobin" in names
        assert "glucose" in names

    async def test_empty_image_raises(self):
        with pytest.raises(ImageParseError, match="empty"):
            await parse_image(b"", "image/jpeg")

    async def test_empty_openai_response_raises(self):
        mock_resp = _make_mock_response("")
        with patch("backend.core.image_parser.AsyncOpenAI") as MockClient:
            instance = MockClient.return_value
            instance.chat.completions.create = AsyncMock(return_value=mock_resp)
            with pytest.raises(ImageParseError, match="empty response"):
                await parse_image(b"bytes", "image/jpeg")

    async def test_no_parameters_extracted_raises(self):
        mock_resp = _make_mock_response("[]")
        with patch("backend.core.image_parser.AsyncOpenAI") as MockClient:
            instance = MockClient.return_value
            instance.chat.completions.create = AsyncMock(return_value=mock_resp)
            with pytest.raises(ImageParseError, match="No blood test parameters"):
                await parse_image(b"bytes", "image/jpeg")

    async def test_rate_limit_raises_image_parse_error(self):
        from openai import RateLimitError as OAIRateLimit
        with patch("backend.core.image_parser.AsyncOpenAI") as MockClient:
            instance = MockClient.return_value
            instance.chat.completions.create = AsyncMock(
                side_effect=OAIRateLimit("rate limit", response=MagicMock(), body={})
            )
            with pytest.raises(ImageParseError, match="rate limit"):
                await parse_image(b"bytes", "image/jpeg")

    async def test_raw_name_preserved(self):
        mock_resp = _make_mock_response('[{"name": "Hb", "value": 14.5, "unit": "g/dL"}]')
        with patch("backend.core.image_parser.AsyncOpenAI") as MockClient:
            instance = MockClient.return_value
            instance.chat.completions.create = AsyncMock(return_value=mock_resp)
            result = await parse_image(b"bytes", "image/png")

        assert result.parameters[0].raw_name == "Hb"
        assert result.parameters[0].name == "hemoglobin"
