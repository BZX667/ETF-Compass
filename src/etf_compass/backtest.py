"""Point-in-time backtesting for long-only ETF rotation portfolios."""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd

from .risk import volatility_target_weights
from .rotation import select_assets

TRADING_DAYS = 252


@dataclass(frozen=True)
class BacktestResult:
    """Daily backtest outputs and summary statistics."""

    equity: pd.Series
    gross_equity: pd.Series
    daily_returns: pd.Series
    positions: pd.DataFrame
    turnover: pd.Series
    metrics: dict[str, float | int]
    benchmark_equity: pd.Series | None = None
    benchmark_metrics: dict[str, float | int] | None = None


def _metrics(returns: pd.Series, annualization: int) -> dict[str, float | int]:
    if returns.empty:
        return {}
    equity = (1.0 + returns).cumprod()
    years = len(returns) / annualization
    annualized_return = float(equity.iloc[-1] ** (1.0 / years) - 1.0) if equity.iloc[-1] > 0 else -1.0
    annualized_volatility = float(returns.std(ddof=1) * math.sqrt(annualization)) if len(returns) > 1 else 0.0
    sharpe = (
        float(returns.mean() * annualization / annualized_volatility)
        if annualized_volatility > 1e-12 else 0.0
    )
    return {
        "total_return": float(equity.iloc[-1] - 1.0),
        "annualized_return": annualized_return,
        "annualized_volatility": annualized_volatility,
        "sharpe": sharpe,
        "max_drawdown": float((equity / equity.cummax() - 1.0).min()),
        "win_rate": float((returns > 0).mean()),
        "trading_days": int(len(returns)),
    }


def run_rotation_backtest(
    close: pd.DataFrame,
    scores: pd.DataFrame,
    *,
    benchmark_close: pd.Series | None = None,
    top_k: int = 4,
    held_buffer_multiple: float = 1.0,
    target_volatility: float = 0.15,
    risk_lookback: int = 20,
    execution_lag: int = 2,
    max_weight: float = 0.35,
    max_gross_exposure: float = 1.0,
    fee: float = 0.0006,
    annualization: int = TRADING_DAYS,
) -> BacktestResult:
    """Backtest daily cross-sectional scores with next-period execution.

    With the default ``execution_lag=2``, scores use the completed close on date
    t, orders execute at the next session's close, and the portfolio earns the
    following close-to-close return. ``execution_lag=1`` is for scores frozen
    before the same date's close; the daily close is then only an approximate
    execution price. Fees are charged per unit of one-way weight turnover.
    Market data is supplied by the caller; this function does not fetch it.
    """
    if not isinstance(close, pd.DataFrame) or close.empty:
        raise ValueError("close must be a non-empty DataFrame")
    if not isinstance(scores, pd.DataFrame) or scores.empty:
        raise ValueError("scores must be a non-empty DataFrame")
    if not scores.index.is_unique or not scores.columns.is_unique:
        raise ValueError("scores index and columns must be unique")
    if not all(pd.api.types.is_numeric_dtype(dtype) for dtype in scores.dtypes):
        raise ValueError("scores must be numeric")
    if not close.index.is_unique or not close.columns.is_unique:
        raise ValueError("close index and columns must be unique")
    if not close.index.is_monotonic_increasing:
        raise ValueError("close index must be sorted in increasing order")
    if not all(pd.api.types.is_numeric_dtype(dtype) for dtype in close.dtypes):
        raise ValueError("close prices must be numeric")
    if np.isinf(close.to_numpy(dtype=float)).any():
        raise ValueError("close prices must be finite or missing")
    if (close.dropna() <= 0).any().any():
        raise ValueError("close prices must be positive")
    if top_k < 1 or risk_lookback < 2 or annualization < 1 or execution_lag not in (1, 2):
        raise ValueError("top_k must be positive, risk_lookback >= 2, annualization >= 1, and execution_lag in {1, 2}")
    if not math.isfinite(fee) or not 0 <= fee < 0.5:
        raise ValueError("fee must be finite and in [0, 0.5)")

    score_panel = scores.replace([np.inf, -np.inf], np.nan).reindex(
        index=close.index, columns=close.columns
    )
    returns = close.pct_change(fill_method=None)
    positions = pd.DataFrame(0.0, index=close.index, columns=close.columns)
    previous: list[str] = []

    for date in close.index:
        row = score_panel.loc[date].dropna()
        if row.empty:
            previous = []
            continue
        candidates = select_assets(
            row,
            top_k=top_k,
            held=previous,
            buffer_multiple=held_buffer_multiple,
        )
        history = returns.loc[:date]
        if execution_lag == 1:
            history = history.iloc[:-1]  # pre-close decisions cannot use today's closing return
        history = history.tail(risk_lookback)
        if len(history) < risk_lookback or not candidates:
            previous = candidates
            continue

        # New listings or gaps do not receive a fabricated risk estimate.
        valid = [
            asset for asset in candidates
            if asset in history and history[asset].replace([np.inf, -np.inf], np.nan).notna().all()
        ]
        if not valid:
            previous = candidates
            continue
        weights = volatility_target_weights(
            history,
            valid,
            target_volatility=target_volatility,
            lookback=risk_lookback,
            max_weight=max_weight,
            max_gross_exposure=max_gross_exposure,
            annualization=annualization,
        )
        positions.loc[date, weights.index] = weights
        previous = weights[weights > 0].index.tolist()

    held = positions.shift(execution_lag).fillna(0.0)
    missing_held_returns = held.gt(0) & returns.isna()
    if missing_held_returns.to_numpy().any():
        raise ValueError("close prices are missing during a held period; repair the history before evaluation")
    active = held.sum(axis=1) > 0
    if not active.any():
        empty = pd.Series(dtype=float, name="return")
        return BacktestResult(
            equity=empty.rename("equity"),
            gross_equity=empty.rename("gross_equity"),
            daily_returns=empty,
            positions=positions,
            turnover=empty.rename("turnover"),
            metrics={},
        )

    start = active[active].index[0]
    gross_returns = (held * returns).sum(axis=1)
    daily_turnover = positions.diff().abs().sum(axis=1)
    daily_turnover.iloc[0] = float(positions.iloc[0].abs().sum())
    # Charge turnover at the close where the rebalance executes: one session
    # after a completed-close signal with lag=2, the same date for a pre-close
    # signal with lag=1. The newly selected weights earn returns only afterward.
    realized_turnover = daily_turnover.shift(execution_lag - 1).fillna(0.0)
    first_cost = realized_turnover[realized_turnover > 0].index
    first_active = active[active].index
    start = min(first_cost[0], first_active[0]) if len(first_cost) else first_active[0]
    net_returns = (gross_returns - realized_turnover * fee).loc[start:]
    gross_returns = gross_returns.loc[start:]
    realized_turnover = realized_turnover.loc[start:]
    equity = (1.0 + net_returns).cumprod().rename("equity")
    gross_equity = (1.0 + gross_returns).cumprod().rename("gross_equity")
    metrics = _metrics(net_returns, annualization)
    metrics["average_turnover"] = float(realized_turnover.mean())
    period_costs = realized_turnover * fee
    prior_equity = (1.0 + net_returns).cumprod().shift(1).fillna(1.0)
    metrics["total_cost"] = float((period_costs * prior_equity).sum())

    benchmark_equity = None
    benchmark_metrics = None
    if benchmark_close is not None:
        if (
            not isinstance(benchmark_close, pd.Series)
            or not benchmark_close.index.is_unique
            or not benchmark_close.index.is_monotonic_increasing
        ):
            raise ValueError("benchmark_close must be a sorted Series with a unique index")
        if not pd.api.types.is_numeric_dtype(benchmark_close.dtype):
            raise ValueError("benchmark prices must be numeric")
        if np.isinf(benchmark_close.to_numpy(dtype=float)).any():
            raise ValueError("benchmark prices must be finite or missing")
        if (benchmark_close.dropna() <= 0).any():
            raise ValueError("benchmark prices must be positive")
        benchmark_returns = benchmark_close.pct_change(fill_method=None).reindex(net_returns.index)
        if benchmark_returns.isna().any() or not np.isfinite(benchmark_returns).all():
            raise ValueError("benchmark_close must cover the full evaluation period and prior close")
        # The evaluation starts at the first portfolio valuation close. Do not
        # credit the benchmark with the price move before that starting point.
        benchmark_returns.iloc[0] = 0.0
        benchmark_equity = (1.0 + benchmark_returns).cumprod().rename("benchmark_equity")
        benchmark_metrics = _metrics(benchmark_returns, annualization)

    return BacktestResult(
        equity=equity,
        gross_equity=gross_equity,
        daily_returns=net_returns.rename("return"),
        positions=positions,
        turnover=realized_turnover.rename("turnover"),
        metrics=metrics,
        benchmark_equity=benchmark_equity,
        benchmark_metrics=benchmark_metrics,
    )


def render_backtest_report(result: BacktestResult, *, title: str = "ETF Rotation Backtest") -> str:
    """Render a compact Markdown performance summary."""
    if result.equity.empty:
        return f"# {title}\n\nNo positions were formed during the evaluation period.\n"

    def percent(key: str, metrics: dict[str, float | int]) -> str:
        return f"{metrics[key]:.2%}"

    metrics = result.metrics
    start, end = result.equity.index[0], result.equity.index[-1]
    lines = [
        f"# {title}",
        "",
        f"Evaluation period: {start} to {end}",
        "",
        "| Metric | Strategy |",
        "| --- | ---: |",
        f"| Total return | {percent('total_return', metrics)} |",
        f"| Annualized return | {percent('annualized_return', metrics)} |",
        f"| Annualized volatility | {percent('annualized_volatility', metrics)} |",
        f"| Sharpe ratio | {metrics['sharpe']:.2f} |",
        f"| Maximum drawdown | {percent('max_drawdown', metrics)} |",
        f"| Win rate | {percent('win_rate', metrics)} |",
        f"| Average daily turnover | {percent('average_turnover', metrics)} |",
        f"| Estimated transaction costs | {percent('total_cost', metrics)} |",
        f"| Trading days | {metrics['trading_days']} |",
    ]
    if result.benchmark_metrics is not None:
        benchmark = result.benchmark_metrics
        lines.extend([
            "",
            "| Metric | Strategy | Benchmark |",
            "| --- | ---: | ---: |",
            f"| Annualized return | {percent('annualized_return', metrics)} | {percent('annualized_return', benchmark)} |",
            f"| Sharpe ratio | {metrics['sharpe']:.2f} | {benchmark['sharpe']:.2f} |",
            f"| Maximum drawdown | {percent('max_drawdown', metrics)} | {percent('max_drawdown', benchmark)} |",
        ])
    lines.extend([
        "",
        "_Results depend on the supplied price history, score timing, execution assumptions, and cost estimate._",
    ])
    return "\n".join(lines) + "\n"
