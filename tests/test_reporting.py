from datetime import date

import pytest

from etf_compass import (
    ForwardObservation,
    IndependentAssessment,
    render_daily_report,
    render_weekly_review,
    score_forward_observations,
)


def test_daily_report_renders_strategy_and_independent_assessment():
    assessment = IndependentAssessment(
        stance="cautious",
        confidence="medium",
        evidence=("Trend weakened",),
        risks=("High volatility",),
        watch_items=("Check next close",),
    )
    report = render_daily_report(
        as_of="2026-10-14",
        market_data_as_of="2026-10-14 15:00 Asia/Shanghai",
        rotation=[{"symbol": "510300", "score": 0.8, "weight": 0.25}],
        assessment=assessment,
        risk_notes=("Check quote coverage",),
    )
    assert "Market data timestamp: 2026-10-14 15:00 Asia/Shanghai" in report
    assert "510300" in report and "25.0%" in report
    assert "Trend weakened" in report and "High volatility" in report
    assert "Account context" not in report


def test_daily_report_rejects_invalid_weight():
    with pytest.raises(ValueError, match="target weights"):
        render_daily_report(
            as_of="2026-10-14",
            market_data_as_of="2026-10-14",
            rotation=[{"symbol": "510300", "score": 1, "weight": 1.2}],
        )


def test_forward_scorecard_uses_only_resolved_observations():
    scorecard = score_forward_observations(
        [
            ForwardObservation(date(2026, 10, 1), date(2026, 10, 7), "positive", 0.04, 0.01),
            ForwardObservation(date(2026, 10, 2), date(2026, 10, 8), "cautious", -0.03, 0.01),
            ForwardObservation(date(2026, 10, 3), date(2026, 10, 9), "neutral", 0.01, 0.00),
            ForwardObservation(date(2026, 10, 10), date(2026, 10, 17), "positive", 0.05, 0.01),
        ],
        as_of=date(2026, 10, 14),
    )
    assert scorecard.evaluated == 3
    assert scorecard.directional == 2
    assert scorecard.hits == 2
    assert scorecard.hit_rate == 1.0
    assert scorecard.mean_signed_excess == pytest.approx(0.035)


def test_forward_observation_requires_a_later_resolution_date():
    with pytest.raises(ValueError, match="follow observed_on"):
        score_forward_observations(
            [ForwardObservation(date(2026, 10, 1), date(2026, 10, 1), "positive", 0.01, 0.0)],
            as_of=date(2026, 10, 14),
        )


def test_weekly_review_includes_forward_scorecard():
    scorecard = score_forward_observations(
        [ForwardObservation(date(2026, 10, 1), date(2026, 10, 7), "positive", 0.03, 0.01)],
        as_of=date(2026, 10, 14),
    )
    report = render_weekly_review(
        period_start="2026-10-07",
        period_end="2026-10-14",
        rotation_review="Rotation was stable.",
        ai_scorecard=scorecard,
        open_questions=("Validate the data source",),
    )
    assert "Directional hit rate: 100.0%" in report
    assert "Mean signed excess return: +2.00%" in report
    assert "Validate the data source" in report


def test_weekly_review_rejects_scorecard_after_review_period():
    scorecard = score_forward_observations([], as_of=date(2026, 10, 15))
    with pytest.raises(ValueError, match="scorecard as_of"):
        render_weekly_review(
            period_start="2026-10-07",
            period_end="2026-10-14",
            rotation_review="Review",
            ai_scorecard=scorecard,
        )
