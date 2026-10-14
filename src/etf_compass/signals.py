"""Reusable price-based ETF signals and simple ensemble aggregation.

Signals are calculated after each bar closes. Callers should execute no
earlier than the next bar and validate their own data and transaction costs.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd


def _check_close(close: pd.DataFrame) -> None:
    if not isinstance(close, pd.DataFrame) or close.empty:
        raise ValueError("close must be a non-empty DataFrame")
    if not close.index.is_unique or not close.columns.is_unique:
        raise ValueError("close index and columns must be unique")
    if not all(pd.api.types.is_numeric_dtype(dtype) for dtype in close.dtypes):
        raise ValueError("close prices must be numeric")
    if (close <= 0).any().any():
        raise ValueError("close prices must be positive")


def _state_signal(entry: pd.DataFrame, exit_: pd.DataFrame) -> pd.DataFrame:
    """Convert entry/exit conditions into a persistent 0/1 position state."""
    state = pd.DataFrame(0.0, index=entry.index, columns=entry.columns)
    for column in entry.columns:
        current = 0.0
        values = []
        for enter, leave in zip(entry[column], exit_[column]):
            if pd.notna(enter) and bool(enter):
                current = 1.0
            elif pd.notna(leave) and bool(leave):
                current = 0.0
            values.append(current)
        state[column] = values
    return state


def turtle_breakout(close: pd.DataFrame, *, entry_window: int = 20, exit_window: int = 10) -> pd.DataFrame:
    """Long-only channel breakout: enter above prior highs, exit below lows."""
    _check_close(close)
    if entry_window < 2 or exit_window < 2:
        raise ValueError("entry_window and exit_window must be >= 2")
    prior_high = close.shift(1).rolling(entry_window, min_periods=entry_window).max()
    prior_low = close.shift(1).rolling(exit_window, min_periods=exit_window).min()
    return _state_signal(close > prior_high, close < prior_low)


def momentum_score(close: pd.DataFrame, *, lookback: int = 120, norm_window: int = 252) -> pd.DataFrame:
    """Volatility-normalized trailing momentum, clipped to [-1, 1]."""
    _check_close(close)
    if lookback < 1 or norm_window < 2:
        raise ValueError("lookback must be >= 1 and norm_window must be >= 2")
    momentum = close.div(close.shift(lookback)).sub(1.0)
    scale = momentum.rolling(norm_window, min_periods=norm_window).std().replace(0, np.nan)
    return momentum.div(scale).replace([np.inf, -np.inf], np.nan).clip(-1, 1)


def dual_momentum_score(close: pd.DataFrame, *, lookback: int = 252) -> pd.DataFrame:
    """Cross-sectional rank of trailing return, gated by positive absolute return."""
    _check_close(close)
    if lookback < 1:
        raise ValueError("lookback must be >= 1")
    trailing = close.div(close.shift(lookback)).sub(1.0)
    relative = trailing.rank(axis=1, pct=True)
    return relative.where(trailing > 0, 0.0)


def mean_reversion_signal(close: pd.DataFrame, *, rsi_window: int = 14, oversold: float = 30.0, exit_rsi: float = 50.0) -> pd.DataFrame:
    """Long-only RSI mean-reversion state: enter oversold, exit on recovery."""
    _check_close(close)
    if rsi_window < 2 or not (0 < oversold < exit_rsi < 100):
        raise ValueError("require rsi_window >= 2 and 0 < oversold < exit_rsi < 100")
    delta = close.diff()
    gains = delta.clip(lower=0).rolling(rsi_window, min_periods=rsi_window).mean()
    losses = (-delta.clip(upper=0)).rolling(rsi_window, min_periods=rsi_window).mean()
    relative_strength = gains.div(losses.replace(0, np.nan))
    rsi = 100 - 100 / (1 + relative_strength)
    rsi = rsi.mask((losses == 0) & (gains > 0), 100.0)
    rsi = rsi.mask((losses == 0) & (gains == 0), 50.0)
    return _state_signal(rsi < oversold, rsi >= exit_rsi)


def volatility_breakout_signal(
    close: pd.DataFrame,
    high: pd.DataFrame,
    low: pd.DataFrame,
    *,
    ema_window: int = 20,
    atr_window: int = 14,
    band_multiple: float = 1.5,
) -> pd.DataFrame:
    """Enter above an EMA+ATR band and exit below the EMA."""
    _check_close(close)
    if not close.index.equals(high.index) or not close.columns.equals(high.columns):
        raise ValueError("high must align with close")
    if not close.index.equals(low.index) or not close.columns.equals(low.columns):
        raise ValueError("low must align with close")
    if ema_window < 2 or atr_window < 2 or not math.isfinite(band_multiple) or band_multiple <= 0:
        raise ValueError("windows must be >= 2 and band_multiple must be positive and finite")
    previous = close.shift(1)
    true_range = pd.DataFrame(
        np.maximum((high - low).to_numpy(), np.maximum((high - previous).abs().to_numpy(), (low - previous).abs().to_numpy())),
        index=close.index,
        columns=close.columns,
    )
    atr = true_range.rolling(atr_window, min_periods=atr_window).mean()
    mid = close.ewm(span=ema_window, adjust=False).mean()
    return _state_signal(close > mid + band_multiple * atr, close < mid)


def equal_weight_ensemble(signals: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Align and average multiple signal panels, clipping the result to [-1, 1]."""
    if not signals:
        raise ValueError("at least one signal panel is required")
    names = list(signals)
    index, columns = signals[names[0]].index, signals[names[0]].columns
    for panel in signals.values():
        if not isinstance(panel, pd.DataFrame):
            raise ValueError("each signal must be a DataFrame")
        index = index.union(panel.index)
        columns = columns.union(panel.columns)
    aligned = [panel.reindex(index=index, columns=columns).fillna(0.0) for panel in signals.values()]
    return (sum(aligned) / len(aligned)).clip(-1, 1)
