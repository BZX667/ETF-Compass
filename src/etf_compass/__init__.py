"""ETF Compass: systematic ETF research and independent AI evaluation."""

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
    "dual_momentum_score",
    "equal_weight_ensemble",
    "mean_reversion_signal",
    "momentum_score",
    "select_assets",
    "turtle_breakout",
    "volatility_breakout_signal",
    "volatility_target_weights",
]
__version__ = "0.1.0"
