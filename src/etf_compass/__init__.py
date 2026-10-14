"""ETF Compass: systematic ETF research and independent AI evaluation."""

from .risk import volatility_target_weights
from .rotation import select_assets

__all__ = ["select_assets", "volatility_target_weights"]
__version__ = "0.1.0"
