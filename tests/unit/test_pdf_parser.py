"""
Tests for pdf_parser.py.

Uses synthetic in-memory PDFs built with reportlab (if available)
or mocks pdfplumber directly.
"""

from unittest.mock import MagicMock, patch

import pytest

from backend.core.pdf_parser import (
    PDFParseError,
    _extract_numeric,
    _find_col_idx,
    parse_pdf,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class TestExtractNumeric:
    def test_plain_number(self):
        assert _extract_numeric("14.5") == 14.5

    def test_number_with_range(self):
        assert _extract_numeric("14.5 (12.0-16.0)") == 14.5

    def test_number_with_flag(self):
        assert _extract_numeric("7200 H") == 7200.0

    def test_comma_formatted(self):
        assert _extract_numeric("250,000") == 250000.0

    def test_no_number_returns_none(self):
        assert _extract_numeric("High") is None

    def test_empty_returns_none(self):
        assert _extract_numeric("") is None


class TestFindColIdx:
    def test_exact_match(self):
        headers = ["test", "value", "unit"]
        assert _find_col_idx(headers, ["value"]) == 1

    def test_first_candidate_wins(self):
        headers = ["parameter", "result", "unit"]
        assert _find_col_idx(headers, ["value", "result"]) == 1

    def test_partial_match_fallback(self):
        headers = ["test name", "observed value", "reference unit"]
        assert _find_col_idx(headers, ["observed"]) == 1

    def test_no_match_returns_none(self):
        assert _find_col_idx(["a", "b"], ["xyz"]) is None


# ---------------------------------------------------------------------------
# parse_pdf with mocked pdfplumber
# ---------------------------------------------------------------------------

def _make_pdf_mock(tables=None, text=""):
    """Build a minimal pdfplumber mock."""
    page = MagicMock()
    page.extract_tables.return_value = tables or []
    page.extract_text.return_value = text

    pdf_mock = MagicMock()
    pdf_mock.pages = [page]
    pdf_mock.__enter__ = MagicMock(return_value=pdf_mock)
    pdf_mock.__exit__ = MagicMock(return_value=False)
    return pdf_mock


class TestParsePDFTableExtraction:
    def test_standard_table(self):
        table = [
            ["Parameter", "Value", "Unit"],
            ["Hemoglobin", "14.5", "g/dL"],
            ["Glucose", "95", "mg/dL"],
        ]
        pdf_mock = _make_pdf_mock(tables=[table])

        with patch("backend.core.pdf_parser.pdfplumber.open", return_value=pdf_mock):
            result = parse_pdf(b"fake_pdf")

        names = [p.name for p in result.parameters]
        assert "hemoglobin" in names
        assert "glucose" in names

    def test_value_with_range_string(self):
        table = [
            ["Test", "Result", "Unit"],
            ["Hemoglobin", "14.5 (12.0-16.0)", "g/dL"],
        ]
        pdf_mock = _make_pdf_mock(tables=[table])

        with patch("backend.core.pdf_parser.pdfplumber.open", return_value=pdf_mock):
            result = parse_pdf(b"fake_pdf")

        assert result.parameters[0].value == 14.5

    def test_unrecognized_parameter(self):
        table = [
            ["Parameter", "Value", "Unit"],
            ["XYZ_Unknown", "99", "units"],
        ]
        pdf_mock = _make_pdf_mock(tables=[table])

        with patch("backend.core.pdf_parser.pdfplumber.open", return_value=pdf_mock):
            result = parse_pdf(b"fake_pdf")

        assert "XYZ_Unknown" in result.unrecognized
        assert len(result.parameters) == 0

    def test_preserves_raw_name(self):
        table = [
            ["Test Name", "Observed Value", "Unit"],
            ["Hb", "14.5", "g/dL"],
        ]
        pdf_mock = _make_pdf_mock(tables=[table])

        with patch("backend.core.pdf_parser.pdfplumber.open", return_value=pdf_mock):
            result = parse_pdf(b"fake_pdf")

        assert result.parameters[0].raw_name == "Hb"
        assert result.parameters[0].name == "hemoglobin"


class TestParsePDFTextFallback:
    def test_text_fallback_when_no_tables(self):
        text = "Hemoglobin    14.5    g/dL\nGlucose    95    mg/dL"
        pdf_mock = _make_pdf_mock(tables=[], text=text)

        with patch("backend.core.pdf_parser.pdfplumber.open", return_value=pdf_mock):
            result = parse_pdf(b"fake_pdf")

        names = [p.name for p in result.parameters]
        assert "hemoglobin" in names
        assert "glucose" in names


class TestParsePDFErrors:
    def test_empty_content_raises(self):
        with pytest.raises(PDFParseError, match="empty"):
            parse_pdf(b"")

    def test_corrupt_pdf_raises(self):
        with patch("backend.core.pdf_parser.pdfplumber.open", side_effect=Exception("corrupt")):
            with pytest.raises(PDFParseError, match="Could not read PDF"):
                parse_pdf(b"not_a_pdf")
