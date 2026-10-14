"""Run an offline, deterministic ETF Compass example."""

from __future__ import annotations

import numpy as np
import pandas as pd

from etf_compass import render_backtest_report, run_rotation_backtest


def main() -> None:
    rng = np.random.default_rng(2026)
    dates = pd.bdate_range("2022-01-03", periods=520)
    daily_returns = pd.DataFrame(
        rng.normal(
            loc=[0.00035, 0.00025, 0.00018, 0.00010],
            scale=[0.010, 0.012, 0.008, 0.006],
            size=(len(dates), 4),
        ),
        index=dates,
        columns=["ETF-A", "ETF-B", "ETF-C", "ETF-D"],
    )
    close = 100.0 * (1.0 + daily_returns).cumprod()
    scores = close.pct_change(63).replace([np.inf, -np.inf], np.nan)

    result = run_rotation_backtest(
        close,
        scores,
        top_k=2,
        target_volatility=0.12,
        risk_lookback=20,
        max_weight=0.50,
        fee=0.0006,
    )
    print(render_backtest_report(result, title="ETF Compass Offline Quickstart"))
    print("\nSynthetic data only; this output is a software demo, not investment evidence.")


if __name__ == "__main__":
    main()
