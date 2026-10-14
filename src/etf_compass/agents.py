"""A lightweight, provider-neutral TradingAgents-style review workflow."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass

from .evaluation import IndependentAssessment, parse_assessment


@dataclass(frozen=True)
class DebateRound:
    round_number: int
    bull: str
    bear: str


@dataclass(frozen=True)
class AgentDiscussion:
    analyst_notes: dict[str, str]
    debate: tuple[DebateRound, ...]
    risk_review: str
    assessment: IndependentAssessment


def run_trading_agents_review(
    facts: Mapping[str, str],
    mechanical_plan: str,
    complete: Callable[[str], str],
    *,
    rounds: int = 2,
) -> AgentDiscussion:
    """Run fact analysts, bull/bear rounds, risk review, and a final PM view.

    ``complete`` is the caller's model adapter, for example a DeepSeek client
    configured outside this package. This function never reads credentials,
    fetches data, stores account state, or places orders.
    """
    if not facts:
        raise ValueError("at least one fact group is required")
    if any(not isinstance(k, str) or not isinstance(v, str) for k, v in facts.items()):
        raise ValueError("facts must map string role names to string evidence")
    if not isinstance(mechanical_plan, str):
        raise ValueError("mechanical_plan must be a string")
    if not callable(complete):
        raise ValueError("complete must be a callable model adapter")
    if not 1 <= rounds <= 5:
        raise ValueError("rounds must be between 1 and 5")

    analyst_notes: dict[str, str] = {}
    for role, evidence in facts.items():
        prompt = (
            f"You are the {role} analyst in an ETF research team. Summarize only the supplied evidence, "
            "separate facts from interpretation, identify uncertainty, and do not issue orders.\n\n"
            f"Evidence:\n{evidence}"
        )
        analyst_notes[role] = complete(prompt)

    context = "\n".join(f"[{role}] {note}" for role, note in analyst_notes.items())
    transcript: list[DebateRound] = []
    for number in range(1, rounds + 1):
        history = "\n".join(
            f"Round {item.round_number} bull: {item.bull}\nRound {item.round_number} bear: {item.bear}"
            for item in transcript
        ) or "No prior debate."
        bull = complete(
            f"You are the bull researcher, debate round {number}/{rounds}. Give the strongest evidence-based "
            f"constructive case and answer prior objections.\nAnalyst notes:\n{context}\nPrior debate:\n{history}"
        )
        bear = complete(
            f"You are the skeptical bear researcher, debate round {number}/{rounds}. Challenge the bull using "
            f"evidence and identify downside or missing data. Do not issue orders.\nAnalyst notes:\n{context}"
            f"\nPrior debate:\n{history}\nBull this round:\n{bull}"
        )
        transcript.append(DebateRound(number, bull, bear))

    debate_text = "\n".join(
        f"Round {item.round_number} bull: {item.bull}\nRound {item.round_number} bear: {item.bear}"
        for item in transcript
    )
    risk_review = complete(
        "You are the risk reviewer. Identify downside scenarios, assumptions, and facts that would invalidate "
        "the analysis. Do not change the mechanical plan or issue orders.\n"
        f"Analyst notes:\n{context}\nDebate:\n{debate_text}\nMechanical plan for context:\n{mechanical_plan}"
    )
    final_raw = complete(
        "You are the portfolio research manager. Summarize the evidence and disagreement as an independent "
        "assessment. The mechanical plan is context only: do not override it or invent an order. "
        "Return only valid JSON with fields stance (positive|neutral|cautious), confidence (low|medium|high), "
        "evidence (array of strings), risks (array of strings), watch_items (array of strings).\n"
        f"Analysts:\n{context}\nDebate:\n{debate_text}\nRisk review:\n{risk_review}\n"
        f"Mechanical plan (context only):\n{mechanical_plan}"
    )
    return AgentDiscussion(
        analyst_notes=analyst_notes,
        debate=tuple(transcript),
        risk_review=risk_review,
        assessment=parse_assessment(final_raw),
    )
