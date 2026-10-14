"""ETF Compass: systematic ETF research and independent AI evaluation."""

from .evaluation import (
    ForwardObservation,
    ForwardScorecard,
    IndependentAssessment,
    score_forward_observations,
)
from .notifications import (
    NotificationError,
    send_email,
    send_report,
    send_serverchan,
    send_wecom_markdown,
)
from .reports import render_daily_report, render_daily_report_html, render_weekly_review
from .risk import volatility_target_weights
from .rotation import select_assets
from .signals import (
    dual_momentum_score,
    equal_weight_ensemble,
    mean_reversion_signal,
    momentum_score,
    turtle_breakout,
    volatility_breakout_signal,
)

__all__ = [
    "ForwardObservation",
    "ForwardScorecard",
    "IndependentAssessment",
    "NotificationError",
    "dual_momentum_score",
    "equal_weight_ensemble",
    "mean_reversion_signal",
    "momentum_score",
    "select_assets",
    "render_daily_report",
    "render_daily_report_html",
    "render_weekly_review",
    "score_forward_observations",
    "send_email",
    "send_report",
    "send_serverchan",
    "send_wecom_markdown",
    "turtle_breakout",
    "volatility_breakout_signal",
    "volatility_target_weights",
]
__version__ = "0.1.0"
