"""Markdown and HTML report rendering for caller-supplied ETF research outputs.

This module formats results only. Callers remain responsible for refreshing
market data, saving point-in-time snapshots, and supplying any private account
context explicitly.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from html import escape

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
    market_coverage: str | None = None,
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
    if market_coverage:
        lines.insert(2, f"Market coverage: {_cell(market_coverage)}")
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


def render_daily_report_html(
    *,
    as_of: str,
    market_data_as_of: str,
    rotation: Sequence[Mapping[str, object]],
    assessment: Mapping[str, object] | IndependentAssessment | None = None,
    risk_notes: Sequence[str] = (),
    plan_summary: str | None = None,
    private_context: str | None = None,
    market_coverage: str | None = None,
) -> str:
    """Render a styled, email-safe HTML daily research report.

    The same inputs as :func:`render_daily_report` are accepted. Account
    context is included verbatim after HTML escaping and should only be sent
    to trusted recipients.
    """
    ranked = sorted(rotation, key=lambda item: float(item["score"]), reverse=True)
    rows: list[str] = []
    for rank, item in enumerate(ranked, 1):
        score = float(item["score"])
        if not math.isfinite(score):
            raise ValueError("rotation scores must be finite")
        weight = item.get("weight")
        if weight is None:
            weight_text = "—"
        else:
            weight = float(weight)
            if not math.isfinite(weight) or not 0 <= weight <= 1:
                raise ValueError("target weights must be finite values between 0 and 1")
            weight_text = f"{weight:.1%}"
        signals = item.get("signals")
        signal_text = (
            ", ".join(f"{escape(str(key))}: {escape(str(value))}" for key, value in signals.items())
            if isinstance(signals, Mapping) and signals
            else "—"
        )
        rows.append(
            "<tr>"
            f'<td style="padding:13px 10px;border-bottom:1px solid #e7e3da;color:#607078">{rank}</td>'
            f'<td style="padding:13px 10px;border-bottom:1px solid #e7e3da;font-weight:700;color:#26333a">{escape(str(item["symbol"]))}</td>'
            f'<td style="padding:13px 10px;border-bottom:1px solid #e7e3da;color:#52656a">{signal_text}</td>'
            f'<td style="padding:13px 10px;border-bottom:1px solid #e7e3da;text-align:right;color:#26333a">{score:.4f}</td>'
            f'<td style="padding:13px 10px;border-bottom:1px solid #e7e3da;text-align:right;font-weight:700;color:#26333a">{weight_text}</td>'
            "</tr>"
        )
    if not rows:
        rows.append(
            '<tr><td colspan="5" style="padding:18px 10px;color:#6e7a7d">No eligible ETF</td></tr>'
        )

    if isinstance(assessment, IndependentAssessment):
        assessment = {
            "stance": assessment.stance,
            "confidence": assessment.confidence,
            "evidence": assessment.evidence,
            "risks": assessment.risks,
            "watch_items": assessment.watch_items,
        }
    assessment = assessment or {}

    def item_list(key: str, label: str) -> str:
        values = assessment.get(key, ())
        if isinstance(values, str):
            values = (values,)
        if not values:
            return ""
        return (
            f'<div style="margin-top:12px;font-size:13px;font-weight:700;color:#52656a">{label}</div>'
            '<ul style="margin:5px 0 0;padding-left:20px">' + "".join(
                f'<li style="padding:2px 0">{escape(str(value))}</li>' for value in values
            ) + "</ul>"
        )

    ai_content = (
        f'<p style="margin:0 0 8px;color:#26333a"><strong>立场：{escape(str(assessment.get("stance", "未提供")))}</strong>'
        f' &nbsp;·&nbsp; 信心：{escape(str(assessment.get("confidence", "—")))}</p>'
        f'{item_list("evidence", "支持依据")}{item_list("risks", "风险因素")}{item_list("watch_items", "后续观察")}'
    ) if assessment else '<p style="margin:0;color:#6e7a7d">未提供 AI 评估。</p>'

    def bullet_list(values: Sequence[str]) -> str:
        if not values:
            return ""
        return "<ul style=\"margin:7px 0 0;padding-left:20px\">" + "".join(
            f'<li style="padding:2px 0">{escape(str(value))}</li>' for value in values
        ) + "</ul>"

    coverage = (
        f'<span style="display:inline-block;margin-left:10px;padding:5px 9px;border-radius:14px;background:#e8efe9;color:#496a57">'
        f'覆盖范围：{escape(market_coverage)}</span>'
        if market_coverage else ""
    )
    plan_card = (
        f'<section style="margin-top:16px;padding:17px 19px;border-radius:8px;background:#f7f3eb">'
        f'<div style="font-size:12px;letter-spacing:1.2px;color:#98684f;font-weight:700">系统化策略计划</div>'
        f'<div style="margin-top:8px;line-height:1.65;color:#26333a">{escape(plan_summary)}</div></section>'
        if plan_summary else ""
    )
    risks_card = (
        f'<section style="margin-top:16px;padding:17px 19px;border-radius:8px;background:#f7f3eb">'
        f'<div style="font-size:12px;letter-spacing:1.2px;color:#98684f;font-weight:700">风险与观察</div>'
        f'{bullet_list(risk_notes)}</section>'
        if risk_notes else ""
    )
    private_card = (
        f'<section style="margin-top:16px;padding:17px 19px;border-radius:8px;background:#f1f3f1">'
        f'<div style="font-size:12px;letter-spacing:1.2px;color:#496a72;font-weight:700">账户信息</div>'
        f'<div style="margin-top:8px;line-height:1.65;color:#26333a">{escape(private_context)}</div></section>'
        if private_context else ""
    )

    return f'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"></head>
<body style="margin:0;padding:24px 12px;background:#f4f1e9;color:#26333a;font-family:Arial,'Noto Sans SC','Microsoft YaHei',sans-serif">
<table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:820px;margin:0 auto;background:#fffefa;border-collapse:separate;border-spacing:0;border-radius:10px;overflow:hidden">
<tr><td style="height:6px;background:#496a72;font-size:0;line-height:0">&nbsp;</td></tr>
<tr><td style="padding:28px 32px 14px">
<div style="font-size:12px;font-weight:700;letter-spacing:1.6px;color:#496a72">ETF COMPASS &nbsp;/&nbsp; 每日研究简报</div>
<h1 style="margin:13px 0 8px;font-family:Georgia,'Noto Serif SC','Songti SC',serif;font-size:28px;line-height:1.3;color:#26333a">市场收盘简报</h1>
<div style="font-size:14px;color:#6e7a7d">{escape(as_of)} &nbsp;·&nbsp; 行情截至 {escape(market_data_as_of)}{coverage}</div>
</td></tr>
<tr><td style="padding:12px 32px 22px">
<div style="margin-bottom:10px;font-size:12px;font-weight:700;letter-spacing:1.2px;color:#6e7a7d">轮动组合与目标仓位</div>
<table width="100%" cellspacing="0" cellpadding="0" style="border-collapse:collapse;font-size:14px">
<thead><tr style="background:#f3f5f1;color:#52656a;text-align:left">
<th style="padding:11px 10px;font-weight:600">排名</th><th style="padding:11px 10px;font-weight:600">ETF</th><th style="padding:11px 10px;font-weight:600">信号</th><th style="padding:11px 10px;text-align:right;font-weight:600">得分</th><th style="padding:11px 10px;text-align:right;font-weight:600">目标仓位</th>
</tr></thead><tbody>{''.join(rows)}</tbody></table>
{plan_card}
<section style="margin-top:16px;padding:18px 20px;border-radius:8px;background:#eef2ef;border-left:4px solid #6d8b78">
<div style="font-size:12px;letter-spacing:1.2px;color:#496a57;font-weight:700">AI 研究摘要</div>
<div style="margin-top:9px;line-height:1.65;font-size:14px;color:#26333a">{ai_content}</div></section>
{risks_card}{private_card}
<div style="padding-top:22px;font-size:12px;line-height:1.5;color:#87918e">ETF Compass · 研究参考，请结合数据与实际情况独立判断</div>
</td></tr></table></body></html>'''


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
