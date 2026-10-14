"""Reproduce a simple ETF momentum-rotation research example from Yahoo Finance."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from etf_compass import render_backtest_report, run_rotation_backtest

TICKERS = ["SPY", "QQQ", "IWM", "TLT", "GLD"]
START = "2010-01-01"
END = "2025-01-01"  # exclusive; freeze the study window at 2010-2024


def download_adjusted_close() -> pd.DataFrame:
    try:
        import yfinance as yf
    except ImportError as exc:
        raise SystemExit("Install the research extra first: python -m pip install -e '.[research]'") from exc

    raw = yf.download(
        TICKERS,
        start=START,
        end=END,
        auto_adjust=True,
        actions=False,
        group_by="column",
        progress=False,
        threads=False,
    )
    if raw is None or raw.empty:
        raise SystemExit("Yahoo Finance returned no rows. Check network access and try again.")
    close = raw["Close"] if isinstance(raw.columns, pd.MultiIndex) else raw[["Close"]]
    close.columns = close.columns.get_level_values(-1) if isinstance(close.columns, pd.MultiIndex) else TICKERS
    close = close.reindex(columns=TICKERS).sort_index().dropna(how="any")
    if close.empty or close.isna().any().any():
        raise SystemExit("Could not form a complete aligned price panel for the fixed ETF universe.")
    return close


def main() -> None:
    close = download_adjusted_close()
    trailing_return = close.div(close.shift(126)).sub(1.0)
    # A non-positive absolute momentum score means no position in that ETF.
    scores = trailing_return.where(trailing_return > 0.0)
    result = run_rotation_backtest(
        close,
        scores,
        benchmark_close=close["SPY"],
        top_k=2,
        target_volatility=0.12,
        risk_lookback=20,
        max_weight=0.50,
        max_gross_exposure=1.0,
        execution_lag=2,
        fee=0.0006,
    )
    report = render_backtest_report(result, title="Public ETF Momentum Research Case")
    data_hash = hashlib.sha256(close.to_csv(float_format="%.8f").encode()).hexdigest()
    metadata = (
        "\n\n## Reproduction details\n\n"
        f"- Data: Yahoo Finance adjusted daily close, downloaded {datetime.now(timezone.utc).date()} (UTC).\n"
        f"- Symbols: {', '.join(TICKERS)}; common complete observations: {len(close)}.\n"
        f"- Requested window: {START} through {END} exclusive.\n"
        "- Signal: positive 126-session price return; select up to two ETFs.\n"
        "- Timing: completed-close signal, next-session close execution, then close-to-close return.\n"
        "- Risk: 12% annualized volatility target, 20-session covariance lookback, 50% single-name cap.\n"
        "- Cost: 6 bps per unit of one-way turnover; excludes spread, market impact, tax, and fund expenses.\n"
        f"- SHA-256 of aligned close panel: `{data_hash}`.\n"
        "- Provider data can be revised; exact results may change when downloaded again.\n"
        "- This is an illustrative historical research case, not a validated live strategy or a return forecast.\n"
    )
    print(report + metadata)
    output = Path("examples/results/public-etf-research-case.md")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(report + metadata, encoding="utf-8")
    print(f"\nWrote {output.resolve()}")


if __name__ == "__main__":
    main()
