"""Portfolio sizing helpers with explicit volatility and exposure limits."""

from __future__ import annotations

import math
from collections.abc import Sequence

import numpy as np
import pandas as pd


def volatility_target_weights(
    returns: pd.DataFrame,
    assets: Sequence[str],
    *,
    target_volatility: float = 0.15,
    lookback: int = 20,
    max_weight: float = 0.35,
    max_gross_exposure: float = 1.0,
    annualization: int = 252,
) -> pd.Series:
    """Build inverse-volatility weights and scale to an annual risk target.

    ``returns`` must contain observations strictly before the intended
    execution period. At least ``lookback`` complete observations are used.
    Weights are long-only, sum to no more than ``max_gross_exposure``, and
    each asset is capped at ``max_weight``. If the caps prevent using the full
    risk budget, the function leaves the remainder in cash.
    """
    if not assets:
        return pd.Series(dtype=float, name="weight")
    if len(set(assets)) != len(assets):
        raise ValueError("assets must be unique")
    if not (math.isfinite(target_volatility) and target_volatility > 0):
        raise ValueError("target_volatility must be positive and finite")
    if lookback < 2 or annualization < 1:
        raise ValueError("lookback must be >= 2 and annualization must be >= 1")
    if not (0 < max_weight <= 1 and 0 < max_gross_exposure <= 1):
        raise ValueError("weight and gross exposure limits must be in (0, 1]")
    if len(assets) * max_weight < 1e-12:
        raise ValueError("combined weight capacity is zero")

    missing = set(assets) - set(returns.columns)
    if missing:
        raise ValueError(f"returns missing assets: {sorted(missing)}")

    sample = returns.loc[:, list(assets)].tail(lookback)
    if len(sample) < lookback:
        raise ValueError(f"need {lookback} prior return observations")
    sample = sample.replace([np.inf, -np.inf], np.nan).dropna(how="any")
    if len(sample) < 2:
        raise ValueError("not enough complete finite observations to estimate risk")

    covariance = sample.cov().to_numpy(dtype=float) * annualization
    daily_vol = sample.std(ddof=1).to_numpy(dtype=float)
    if not np.isfinite(covariance).all() or not np.isfinite(daily_vol).all():
        raise ValueError("risk estimates are not finite")

    # Equal risk contribution starts from inverse volatility. Degenerate
    # zero-vol assets receive no artificial infinite allocation.
    annual_vol = daily_vol * math.sqrt(annualization)
    inv_vol = np.divide(1.0, annual_vol, out=np.zeros_like(annual_vol), where=annual_vol > 1e-12)
    if inv_vol.sum() <= 0:
        base = np.full(len(assets), 1.0 / len(assets))
    else:
        base = inv_vol / inv_vol.sum()

    estimated_vol = math.sqrt(max(float(base @ covariance @ base), 0.0))
    gross = min(max_gross_exposure, target_volatility / estimated_vol) if estimated_vol > 1e-12 else 0.0
    weights = base * gross

    # Cap names; redistribute available exposure to uncapped names until no
    # capacity remains. This preserves long-only weights and the gross limit.
    for _ in range(len(assets) + 1):
        excess = np.maximum(weights - max_weight, 0.0)
        if excess.sum() <= 1e-12:
            break
        weights = np.minimum(weights, max_weight)
        room = np.maximum(max_weight - weights, 0.0)
        if room.sum() <= 1e-12:
            break
        weights += room / room.sum() * min(float(excess.sum()), float(room.sum()))

    total = float(weights.sum())
    if total > max_gross_exposure:
        weights *= max_gross_exposure / total
    return pd.Series(weights, index=list(assets), name="weight")
