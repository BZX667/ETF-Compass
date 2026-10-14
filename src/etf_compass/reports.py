"""Markdown report rendering for caller-supplied ETF research outputs.

This module formats results only. Callers remain responsible for refreshing
market data, saving point-in-time snapshots, and supplying any private account
context explicitly.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence

from .evaluation import ForwardScorecard, IndependentAssessment


def _cell(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ").strip()


def render_daily_report(
    *,
    as_of: str,
    market_data_as_of: str,
    rotation: Sequence[Mapping[str, object]],
    assessment: Mapping[str, object] | IndependentAssessment | None = None,
    risk_notes: Sequence[str] = (),
    plan_summary: str | None = None,
    private_context: str | None = None,
) -> str:
    """Render a daily report from fresh, already-computed application data.

    Each rotation item must include ``symbol`` and ``score``. ``weight`` and
    ``signals`` are optional. ``private_context`` is included verbatim and is
    intentionally opt-in; supply it only for trusted recipients.
    """
    lines = [
        f"# ETF Compass Daily Report — {_cell(as_of)}",
        f"Market data timestamp: {_cell(market_data_as_of)}",
        "",
        "## Rotation and target weights",
        "| Rank | ETF | Score | Target weight |",
        "| ---: | --- | ---: | ---: |",
    ]
    ranked = sorted(rotation, key=lambda item: float(item["score"]), reverse=True)
    signal_lines: list[str] = []
    if not ranked:
        lines.append("| — | No eligible ETF | — | — |")
    for rank, item in enumerate(ranked, 1):
        score = float(item["score"])
        weight = item.get("weight")
        if not math.isfinite(score):
            raise ValueError("rotation scores must be finite")
        if weight is None:
            weight_text = "—"
        else:
            weight = float(weight)
            if not math.isfinite(weight) or not 0 <= weight <= 1:
                raise ValueError("target weights must be finite values between 0 and 1")
            weight_text = f"{weight:.1%}"
        lines.append(
            f"| {rank} | {_cell(item['symbol'])} | {score:.4f} | {weight_text} |"
        )
        signals = item.get("signals")
        if isinstance(signals, Mapping) and signals:
            details = ", ".join(f"{_cell(k)}: {_cell(v)}" for k, v in signals.items())
            signal_lines.append(f"- {_cell(item['symbol'])}: {details}")

    if signal_lines:
        lines.extend(["", "Signal details", *signal_lines])

    if plan_summary:
        lines.extend(["", "## Mechanical plan", plan_summary.strip()])
    lines.extend(["", "## Independent AI assessment"])
    if assessment:
        if isinstance(assessment, IndependentAssessment):
            assessment = {
                "stance": assessment.stance,
                "confidence": assessment.confidence,
                "evidence": assessment.evidence,
                "risks": assessment.risks,
                "watch_items": assessment.watch_items,
            }
        lines.extend(
            [
                f"- Stance: {_cell(assessment.get('stance', '—'))}",
                f"- Confidence: {_cell(assessment.get('confidence', '—'))}",
            ]
        )
        for key, label in (("evidence", "Evidence"), ("risks", "Risks"), ("watch_items", "Watch items")):
            values = assessment.get(key, ())
            if values:
                lines.append(f"- {label}:")
                lines.extend(f"  - {_cell(value)}" for value in values)
    else:
        lines.append("- No AI assessment supplied.")

    if risk_notes:
        lines.extend(["", "## Risk notes", *(f"- {_cell(note)}" for note in risk_notes)])
    if private_context:
        lines.extend(["", "## Account context", private_context.strip()])
    return "\n".join(lines).rstrip() + "\n"


def render_weekly_review(
    *,
    period_start: str,
    period_end: str,
    rotation_review: str,
    ai_scorecard: ForwardScorecard | None = None,
    open_questions: Sequence[str] = (),
    private_context: str | None = None,
) -> str:
    """Render a weekly research review; account content is opt-in."""
    from datetime import date

    try:
        end_date = date.fromisoformat(period_end)
    except ValueError:
        raise ValueError("period_end must be an ISO date") from None
    if ai_scorecard is not None and ai_scorecard.as_of > end_date:
        raise ValueError("scorecard as_of must not be later than period_end")
    lines = [
        f"# ETF Compass Weekly Review — {_cell(period_start)} to {_cell(period_end)}",
        "",
        "## Systematic rotation",
        rotation_review.strip() or "No rotation review supplied.",
        "",
        "## Forward evaluation of AI views",
    ]
    if ai_scorecard is None:
        lines.append("No resolved forward observations are available.")
    else:
        hit_rate = "—" if ai_scorecard.hit_rate is None else f"{ai_scorecard.hit_rate:.1%}"
        mean_score = "—" if ai_scorecard.mean_signed_excess is None else f"{ai_scorecard.mean_signed_excess:+.2%}"
        lines.extend(
            [
                f"- Resolved observations: {ai_scorecard.evaluated}",
                f"- Directional observations: {ai_scorecard.directional}",
                f"- Directional hit rate: {hit_rate}",
                f"- Mean signed excess return: {mean_score}",
            ]
        )
    if open_questions:
        lines.extend(["", "## Open questions", *(f"- {_cell(item)}" for item in open_questions)])
    if private_context:
        lines.extend(["", "## Account context", private_context.strip()])
    lines.extend(["", "_Forward metrics use only observations resolved by the review date._"])
    return "\n".join(lines).rstrip() + "\n"
