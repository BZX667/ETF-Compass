"""Reproduce a Chinese-listed ETF momentum-rotation backtest."""

from __future__ import annotations

import hashlib
import math
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from etf_compass import BacktestResult, run_rotation_backtest

SYMBOLS = {
    "510050": "上证50",
    "510300": "沪深300",
    "510500": "中证500",
    "159915": "创业板",
    "513100": "纳指100 QDII",
    "513500": "标普500 QDII",
    "513030": "德国DAX QDII",
    "518880": "黄金",
    "511010": "国债",
}
START = "2015-01-01"
END = "2025-01-01"  # exclusive; fixed 2015-2024 study window


def download_adjusted_close() -> pd.DataFrame:
    try:
        import yfinance as yf
    except ImportError as exc:
        raise SystemExit("请先安装研究依赖：python -m pip install -e '.[research]'") from exc

    tickers = [f"{code}.{'SZ' if code.startswith('15') else 'SS'}" for code in SYMBOLS]
    raw = yf.download(
        tickers,
        start=START,
        end=END,
        auto_adjust=True,
        actions=False,
        group_by="column",
        progress=False,
        threads=False,
    )
    if raw is None or raw.empty:
        raise SystemExit("未能获取行情数据，请检查网络后重试。")

    close = raw["Close"].copy()
    close.columns = [str(ticker).split(".")[0] for ticker in close.columns]
    close = close.reindex(columns=list(SYMBOLS)).sort_index().dropna(how="any")
    if close.empty or close.isna().any().any():
        raise SystemExit("固定 ETF 范围内没有足够的共同有效行情。")
    return close


def run_case(close: pd.DataFrame, top_k: int) -> BacktestResult:
    trailing_return = close.div(close.shift(126)).sub(1.0)
    scores = trailing_return.where(trailing_return > 0.0)
    return run_rotation_backtest(
        close,
        scores,
        benchmark_close=close["510300"],
        top_k=top_k,
        target_volatility=0.12,
        risk_lookback=20,
        max_weight=0.35,
        max_gross_exposure=1.0,
        execution_lag=2,
        fee=0.0006,
    )


def pct(metrics: dict[str, float | int], key: str) -> str:
    return f"{metrics[key]:.2%}"


def render_equity_chart(result: BacktestResult, output: Path) -> None:
    """Write a compact SVG comparing strategy and benchmark equity curves."""
    if result.equity.empty or result.benchmark_equity is None:
        return

    left, top, plot_width, plot_height = 70, 64, 800, 230
    series = [result.equity, result.benchmark_equity]
    low = min(float(values.min()) for values in series)
    high = max(float(values.max()) for values in series)
    y_min = min(0.5, math.floor(low * 2) / 2)
    y_max = max(1.5, math.ceil(high * 2) / 2)
    y_range = max(y_max - y_min, 0.5)

    def points(values: pd.Series) -> str:
        count = max(len(values) - 1, 1)
        coords = []
        for i, value in enumerate(values.to_numpy(dtype=float)):
            x = left + i / count * plot_width
            y = top + (y_max - value) / y_range * plot_height
            coords.append(f"{x:.1f},{y:.1f}")
        return " ".join(coords)

    first_date = pd.Timestamp(result.equity.index[0])
    last_date = pd.Timestamp(result.equity.index[-1])
    chart = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="940" height="360" viewBox="0 0 940 360" role="img" aria-labelledby="title desc">',
        '<title id="title">ETF 轮动回测净值曲线</title><desc id="desc">ETF 轮动组合与沪深300 ETF 的历史净值对比。</desc>',
        '<rect width="940" height="360" rx="14" fill="#fffefa"/>',
        '<text x="34" y="34" font-family="Arial,sans-serif" font-size="15" font-weight="700" fill="#67547d">回测净值对比</text>',
        '<line x1="590" y1="30" x2="614" y2="30" stroke="#70558f" stroke-width="3"/><text x="622" y="34" font-family="Arial,sans-serif" font-size="12" fill="#332b45">ETF 轮动 Top 3</text>',
        '<line x1="770" y1="30" x2="794" y2="30" stroke="#899397" stroke-width="2.5"/><text x="802" y="34" font-family="Arial,sans-serif" font-size="12" fill="#332b45">沪深 300</text>',
    ]

    for tick in [y_min + i * 0.5 for i in range(int(round((y_max - y_min) / 0.5)) + 1)]:
        y = top + (y_max - tick) / y_range * plot_height
        chart.append(f'<line x1="{left}" y1="{y:.0f}" x2="{left + plot_width}" y2="{y:.0f}" stroke="#e6e1d9"/>')
        chart.append(f'<text x="{left - 10}" y="{y + 4:.0f}" text-anchor="end" font-family="Arial,sans-serif" font-size="11" fill="#738084">{tick:.1f}×</text>')
    chart.extend([
        f'<polyline points="{points(result.benchmark_equity)}" fill="none" stroke="#899397" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round"/>',
        f'<polyline points="{points(result.equity)}" fill="none" stroke="#70558f" stroke-width="3.5" stroke-linejoin="round" stroke-linecap="round"/>',
        f'<text x="{left}" y="{top + plot_height + 24}" font-family="Arial,sans-serif" font-size="11" fill="#738084">{first_date:%Y-%m}</text>',
        f'<text x="{left + plot_width}" y="{top + plot_height + 24}" text-anchor="end" font-family="Arial,sans-serif" font-size="11" fill="#738084">{last_date:%Y-%m}</text>',
        '<text x="34" y="338" font-family="Arial,sans-serif" font-size="11" fill="#738084">复权净值 · 已计模型换手成本 · 收盘信号 / 次日收盘成交</text>',
        '</svg>',
    ])
    output.write_text("\n".join(chart), encoding="utf-8")


def main() -> None:
    close = download_adjusted_close()
    result = run_case(close, top_k=3)
    top_two = run_case(close, top_k=2)
    benchmark = result.benchmark_metrics or {}
    names = ", ".join(f"{code} {name}" for code, name in SYMBOLS.items())
    data_hash = hashlib.sha256(close.to_csv(float_format="%.8f").encode()).hexdigest()
    report = f"""# A 股市场挂牌 ETF 动量轮动回测案例

## 主要结果

| 指标 | ETF 轮动（Top 3） | 沪深 300 ETF 持有 |
| --- | ---: | ---: |
| 累计收益 | {pct(result.metrics, 'total_return')} | {pct(benchmark, 'total_return')} |
| 年化收益 | {pct(result.metrics, 'annualized_return')} | {pct(benchmark, 'annualized_return')} |
| 年化波动率 | {pct(result.metrics, 'annualized_volatility')} | {pct(benchmark, 'annualized_volatility')} |
| Sharpe | {result.metrics['sharpe']:.2f} | {benchmark['sharpe']:.2f} |
| 最大回撤 | {pct(result.metrics, 'max_drawdown')} | {pct(benchmark, 'max_drawdown')} |

Top 2 敏感性结果：累计收益 {pct(top_two.metrics, 'total_return')}，年化收益 {pct(top_two.metrics, 'annualized_return')}，Sharpe {top_two.metrics['sharpe']:.2f}。

## 复现口径

- 样本期：{result.equity.index[0].date()} 至 {result.equity.index[-1].date()}；固定数据请求区间为 {START} 至 {END}（结束日期不含）。
- ETF 范围：{names}。
- 信号：过去 126 个交易日正动量；选择排名靠前的 3 只，非正动量标的不持仓。
- 时序：T 日收盘生成评分，T+1 日收盘模拟成交，之后开始计算持仓收益；不使用同日收盘价成交。
- 仓位：此前 20 日估算波动，年化目标 12%，单 ETF 上限 35%，组合总敞口不超过 100%。
- 成本：按单边换手计 6 bp；未包含买卖价差、冲击、税费、申赎成本、QDII 溢价波动及基金费用。
- 交易日数：{result.metrics['trading_days']}；平均单日换手：{pct(result.metrics, 'average_turnover')}；估算累计成本：{pct(result.metrics, 'total_cost')}（占初始资金估算）。
- 对齐后复权收盘价面板 SHA-256：`{data_hash}`。
- 数据可能被修订；再次下载的哈希和结果可能变化。QDII 受跨市场时差及溢价影响，本例不等同于对其净值或盘中成交的验证。

这是固定 ETF 范围上的历史回测演示，存在标的选择偏差的可能，不能据此推断未来收益，也不是投资建议。
"""
    output = Path("examples/results/china-etf-rotation-case.md")
    output.parent.mkdir(parents=True, exist_ok=True)
    render_equity_chart(result, output.with_name("china-etf-rotation-equity.svg"))
    report = report.replace(
        "## 主要结果\n",
        "## 净值曲线\n\n"
        '<div align="center">\n'
        '  <img src="china-etf-rotation-equity.svg" alt="ETF 轮动与沪深300 ETF 回测净值曲线" width="100%">\n'
        '</div>\n\n'
        "## 主要结果\n",
        1,
    )
    print(report)
    output.write_text(report, encoding="utf-8")
    print(f"\n报告已写入：{output.resolve()}")


if __name__ == "__main__":
    print(f"行情下载时间：{datetime.now(timezone.utc).date()} UTC")
    main()
