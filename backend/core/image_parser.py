"""
Image-based blood report parser using Gemini Vision.

Accepts a JPG/PNG/WEBP photo of a blood report and extracts blood parameters
using gemini-2.0-flash's vision capability. Returns the same BloodParameter format
as the CSV parser, so the rest of the pipeline (validator, reference ranges,
simplifier) works unchanged.

Flow:
  image bytes -> base64 encode -> Gemini vision prompt -> JSON response -> BloodParameter list
"""

import base64
import json
import re
from dataclasses import dataclass

import structlog
from openai import AsyncOpenAI, APIError, APITimeoutError, RateLimitError

from backend.config import settings
from backend.core.parser import BloodParameter, ParseResult, normalize_name

logger = structlog.get_logger()

_GROQ_BASE_URL = "https://api.groq.com/openai/v1"
_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"

SUPPORTED_MIME_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}

_EXTRACTION_SYSTEM_PROMPT = """You are a medical data extraction assistant.
Your ONLY job is to extract blood test parameter values from the image and return them as JSON.
Do NOT explain, summarize, or add any commentary.
"""

_EXTRACTION_USER_PROMPT = """Look at this blood test report image and extract ALL blood test parameters.

Return ONLY a valid JSON array. No markdown, no code blocks, no explanation -- raw JSON only.

Each item in the array must have exactly these fields:
- "name": the test parameter name exactly as it appears in the report
- "value": the numeric result (number only, no units)
- "unit": the unit of measurement (string, empty string if not shown)

Example output format:
[
  {"name": "Hemoglobin", "value": 14.5, "unit": "g/dL"},
  {"name": "WBC", "value": 7200, "unit": "/uL"},
  {"name": "Glucose", "value": 95, "unit": "mg/dL"}
]

Rules:
- Only include rows that have a clear numeric result
- Skip rows that are text-only headers, ranges, or flags
- If a value has a range like "12.0-16.0", skip it -- only include the patient's actual result
- If you cannot read a value clearly, skip that row
- Return an empty array [] if no blood parameters are found
"""


class ImageParseError(Exception):
    pass


def _encode_image(content: bytes) -> str:
    return base64.standard_b64encode(content).decode("utf-8")


def _extract_json_from_response(text: str) -> list[dict]:
    """
    Extract JSON array from model response, handling cases where
    the model wraps output in markdown code blocks despite instructions.
    """
    text = text.strip()

    # Strip markdown code fences if present
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    text = text.strip()

    try:
        data = json.loads(text)
        if isinstance(data, list):
            return data
        raise ImageParseError("Expected a JSON array but got a different type.")
    except json.JSONDecodeError as exc:
        raise ImageParseError(f"Model returned invalid JSON: {exc}") from exc


def _build_parameters(raw_items: list[dict]) -> ParseResult:
    """Convert raw JSON items into BloodParameter objects."""
    parameters: list[BloodParameter] = []
    unrecognized: list[str] = []

    for item in raw_items:
        raw_name = str(item.get("name", "")).strip()
        raw_value = item.get("value")
        unit = str(item.get("unit", "")).strip()

        if not raw_name:
            continue

        try:
            value = float(raw_value)
        except (TypeError, ValueError):
            unrecognized.append(raw_name)
            continue

        canonical = normalize_name(raw_name)
        if canonical is None:
            unrecognized.append(raw_name)
            continue

        parameters.append(BloodParameter(
            name=canonical,
            raw_name=raw_name,
            value=value,
            unit=unit,
        ))

    return ParseResult(parameters=parameters, unrecognized=unrecognized)


async def parse_image(content: bytes, mime_type: str) -> ParseResult:
    """
    Extract blood parameters from an image using Gemini Vision.

    Args:
        content:   Raw image bytes
        mime_type: MIME type string, e.g. "image/jpeg"

    Returns:
        ParseResult with the same structure as parse_csv()

    Raises:
        ImageParseError: If extraction fails or API is unavailable
    """
    if not content:
        raise ImageParseError("Image file is empty.")

    b64 = _encode_image(content)
    client = AsyncOpenAI(
        api_key=settings.groq_api_key,
        base_url=_GROQ_BASE_URL,
        timeout=60.0,
    )

    try:
        response = await client.chat.completions.create(
            model=_MODEL,
            temperature=0.0,
            max_tokens=1000,
            messages=[
                {"role": "system", "content": _EXTRACTION_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{b64}",
                                "detail": "high",
                            },
                        },
                        {
                            "type": "text",
                            "text": _EXTRACTION_USER_PROMPT,
                        },
                    ],
                },
            ],
        )
    except RateLimitError as exc:
        raise ImageParseError("Groq rate limit reached. Please try again shortly.") from exc
    except APITimeoutError as exc:
        raise ImageParseError("Groq request timed out. Please try again.") from exc
    except APIError as exc:
        raise ImageParseError(f"Groq API error: {exc}") from exc

    raw_text = response.choices[0].message.content or ""
    logger.info("image_extraction_raw", length=len(raw_text))

    if not raw_text.strip():
        raise ImageParseError("Groq returned an empty response for the image.")

    raw_items = _extract_json_from_response(raw_text)

    if not raw_items:
        raise ImageParseError(
            "No blood test parameters could be extracted from the image. "
            "Please ensure the image is clear and contains a blood test report."
        )

    result = _build_parameters(raw_items)
    logger.info(
        "image_parsed",
        extracted=len(raw_items),
        recognized=len(result.parameters),
        unrecognized=len(result.unrecognized),
    )
    return result
