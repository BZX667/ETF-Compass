"""Provider-neutral LLM assessment schema and prompt builder."""

from __future__ import annotations

import json
import math
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from typing import Any


@dataclass(frozen=True)
class IndependentAssessment:
    """A structured AI view that remains separate from portfolio decisions."""

    stance: str
    confidence: str
    evidence: tuple[str, ...]
    risks: tuple[str, ...]
    watch_items: tuple[str, ...]


@dataclass(frozen=True)
class ForwardObservation:
    """A saved AI view paired with a later asset and benchmark return."""

    observed_on: date
    resolved_on: date
    stance: str
    asset_return: float
    benchmark_return: float


@dataclass(frozen=True)
class ForwardScorecard:
    """Directional quality of resolved positive/cautious AI views."""

    as_of: date
    evaluated: int
    directional: int
    hits: int
    hit_rate: float | None
    mean_signed_excess: float | None


def score_forward_observations(
    observations: Iterable[ForwardObservation],
    *,
    as_of: date,
) -> ForwardScorecard:
    """Score only views whose outcome was observable by ``as_of``.

    Positive views count as correct when the asset beats its benchmark;
    cautious views count as correct when it underperforms. Neutral views are
    counted as evaluated but excluded from directional hit rate and mean
    signed excess. Returns are decimal fractions (for example, ``0.02``).
    """
    resolved: list[ForwardObservation] = []
    for item in observations:
        if item.observed_on >= item.resolved_on:
            raise ValueError("resolved_on must follow observed_on")
        if item.stance not in {"positive", "neutral", "cautious"}:
            raise ValueError("stance must be positive, neutral, or cautious")
        if not all(math.isfinite(value) for value in (item.asset_return, item.benchmark_return)):
            raise ValueError("forward returns must be finite")
        if item.resolved_on <= as_of:
            resolved.append(item)

    directional = [item for item in resolved if item.stance != "neutral"]
    signed_excess = [
        (1.0 if item.stance == "positive" else -1.0)
        * (item.asset_return - item.benchmark_return)
        for item in directional
    ]
    hits = sum(value > 0 for value in signed_excess)
    return ForwardScorecard(
        as_of=as_of,
        evaluated=len(resolved),
        directional=len(directional),
        hits=hits,
        hit_rate=(hits / len(directional)) if directional else None,
        mean_signed_excess=(sum(signed_excess) / len(signed_excess)) if signed_excess else None,
    )


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
