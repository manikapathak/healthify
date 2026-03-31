"""
Groq-powered blood report simplifier.

Converts parsed blood parameters + reference range comparisons into
plain-English explanations suitable for a non-medical audience.

Design decisions:
  - Model: llama-3.3-70b-versatile (free tier, high quality)
  - Temperature: 0.3 (consistency over creativity)
  - Max tokens: 1500
  - Response caching: identical inputs return cached result
  - Graceful degradation: returns None on API errors (caller decides fallback)
"""

import hashlib
import json
from dataclasses import dataclass
from functools import lru_cache

import structlog
from openai import AsyncOpenAI, APIError, APITimeoutError, RateLimitError

from backend.config import settings
from backend.core.parser import BloodParameter
from backend.ml.reference_ranges import RangeResult

logger = structlog.get_logger()

_GROQ_BASE_URL = "https://api.groq.com/openai/v1"
_MODEL = "llama-3.3-70b-versatile"

_SYSTEM_PROMPT = """You are a clinical report interpreter writing for a general audience.

Your role is to translate blood test results into clear, professional prose that a patient
can read and understand without a medical background.

WRITING STYLE:
- Write in the tone of a knowledgeable, calm clinician. Not casual, not robotic.
- Use plain sentences. No bullet points, no numbered lists, no headers.
- Write in flowing paragraphs. Each parameter gets two to three concise sentences.
- Do not use em dashes (--) or hyphens used as dashes. Use commas or full stops instead.
- Do not use emojis or any symbols other than standard punctuation.
- Do not begin any sentence with "I" or use first-person language.
- Avoid filler phrases such as "It is important to note", "Please be aware", "It should be mentioned".
- Do not use words like "amazing", "great", "wonderful", or other informal praise.
- Never use markdown formatting of any kind.

CONTENT RULES:
- For each parameter: state what it measures, whether the result is within the normal range,
  and what a deviation (if any) generally indicates in practical health terms.
- Do not diagnose any condition or disease.
- Do not recommend specific medications, supplements, or treatments.
- For any result that falls outside the normal range, include the sentence:
  "A consultation with a physician is advisable to evaluate this finding."
- End the entire response with this exact sentence on its own line:
  "This report is provided for informational purposes only and does not constitute medical advice. A qualified healthcare professional should be consulted for interpretation of these results."
"""


@dataclass(frozen=True)
class ParameterExplanation:
    parameter: str
    value: float
    unit: str
    status: str        # low / normal / high
    explanation: str


@dataclass(frozen=True)
class SimplificationResult:
    explanations: list[ParameterExplanation]
    summary: str
    cached: bool = False


class SimplifierError(Exception):
    pass


def _build_prompt(
    parameters: list[BloodParameter],
    ranges: dict[str, RangeResult],
) -> str:
    lines = [
        "The following blood test results require a professional written interpretation.\n",
        "Write a clear, factual explanation of each parameter for a general audience. "
        "Use plain prose only. No bullet points. No em dashes. No emojis. No markdown.\n",
    ]

    for param in parameters:
        ref = ranges.get(param.name)
        if ref:
            status = ref.classify(param.value)
            normal_range = f"{ref.low} to {ref.high} {ref.unit}"
        else:
            status = "unknown"
            normal_range = "not available"

        label = param.name.replace("_", " ").title()
        lines.append(
            f"{label}: {param.value} {param.unit} "
            f"| Status: {status} | Reference range: {normal_range}"
        )

    lines.append(
        "\nAfter addressing each parameter individually, write a brief overall summary paragraph."
    )
    return "\n".join(lines)


def _cache_key(parameters: list[BloodParameter], ranges: dict[str, RangeResult]) -> str:
    """Deterministic hash of inputs for caching."""
    data = {
        "params": [(p.name, p.value, p.unit) for p in sorted(parameters, key=lambda x: x.name)],
    }
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()


# Simple in-memory cache (process lifetime)
_cache: dict[str, SimplificationResult] = {}


@lru_cache(maxsize=1)
def _get_client() -> AsyncOpenAI:
    return AsyncOpenAI(
        api_key=settings.groq_api_key,
        base_url=_GROQ_BASE_URL,
        timeout=30.0,
    )


async def simplify(
    parameters: list[BloodParameter],
    ranges: dict[str, RangeResult],
) -> SimplificationResult | None:
    """
    Call Gemini to explain blood parameters in plain English.

    Returns None on API failure — callers should handle gracefully.
    """
    if not parameters:
        return None

    key = _cache_key(parameters, ranges)
    if key in _cache:
        cached = _cache[key]
        return SimplificationResult(
            explanations=cached.explanations,
            summary=cached.summary,
            cached=True,
        )

    prompt = _build_prompt(parameters, ranges)

    try:
        client = _get_client()
        response = await client.chat.completions.create(
            model=_MODEL,
            temperature=0.3,
            max_tokens=1500,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
        )
    except RateLimitError:
        logger.warning("groq_rate_limit")
        return None
    except APITimeoutError:
        logger.warning("groq_timeout")
        return None
    except APIError as exc:
        logger.error("groq_error", error=str(exc))
        return None

    raw_text = response.choices[0].message.content or ""

    # Build per-parameter explanations from range data
    explanations = [
        ParameterExplanation(
            parameter=p.name,
            value=p.value,
            unit=p.unit,
            status=ranges[p.name].classify(p.value) if p.name in ranges else "unknown",
            explanation="",  # Full explanation is in the summary text
        )
        for p in parameters
    ]

    result = SimplificationResult(
        explanations=explanations,
        summary=raw_text,
        cached=False,
    )
    _cache[key] = result
    return result
