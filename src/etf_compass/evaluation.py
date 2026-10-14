"""Provider-neutral LLM assessment schema and prompt builder."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class IndependentAssessment:
    """A structured AI view that remains separate from portfolio decisions."""

    stance: str
    confidence: str
    evidence: tuple[str, ...]
    risks: tuple[str, ...]
    watch_items: tuple[str, ...]


def build_assessment_prompt(market_facts: str, mechanical_plan: str) -> str:
    """Build a constrained prompt for an external LLM provider.

    No model provider, account information, or trading API is included in this
    package. Callers decide what public market facts to provide.
    """
    return f"""You are an independent ETF research analyst. Assess the supplied facts; do not issue orders, invent prices, or change the mechanical plan. Clearly separate evidence from uncertainty. Return only valid JSON matching this schema:
{{"stance":"positive|neutral|cautious","confidence":"low|medium|high","evidence":["..."],"risks":["..."],"watch_items":["..."]}}

Market facts:
{market_facts}

Mechanical plan (context only; do not override):
{mechanical_plan}
"""


def parse_assessment(response: str) -> IndependentAssessment:
    """Validate a model response against the public assessment schema."""
    try:
        payload: Any = json.loads(response)
    except json.JSONDecodeError as exc:
        raise ValueError("assessment must be a JSON object") from exc
    if not isinstance(payload, dict):
        raise ValueError("assessment must be a JSON object")

    allowed = {
        "stance": {"positive", "neutral", "cautious"},
        "confidence": {"low", "medium", "high"},
    }
    for key, values in allowed.items():
        if payload.get(key) not in values:
            raise ValueError(f"{key} must be one of {sorted(values)}")

    def strings(key: str) -> tuple[str, ...]:
        value = payload.get(key)
        if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
            raise ValueError(f"{key} must be a list of strings")
        return tuple(item.strip() for item in value if item.strip())

    return IndependentAssessment(
        stance=payload["stance"],
        confidence=payload["confidence"],
        evidence=strings("evidence"),
        risks=strings("risks"),
        watch_items=strings("watch_items"),
    )
