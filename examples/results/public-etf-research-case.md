# Public ETF Momentum Research Case

Evaluation period: 2010-07-07 00:00:00 to 2024-12-31 00:00:00

| Metric | Strategy |
| --- | ---: |
| Total return | 147.30% |
| Annualized return | 6.46% |
| Annualized volatility | 11.13% |
| Sharpe ratio | 0.62 |
| Maximum drawdown | -20.51% |
| Win rate | 52.76% |
| Average daily turnover | 11.59% |
| Estimated transaction costs | 43.68% |
| Trading days | 3647 |

| Metric | Strategy | Benchmark |
| --- | ---: | ---: |
| Annualized return | 6.46% | 5.11% |
| Sharpe ratio | 0.62 | 0.40 |
| Maximum drawdown | -20.51% | -45.56% |

_Results depend on the supplied price history, score timing, execution assumptions, and cost estimate._


## Reproduction details

- Data: Yahoo Finance adjusted daily close, downloaded 2026-10-14 (UTC).
- Symbols: SPY, QQQ, IWM, TLT, GLD; common complete observations: 3774.
- Requested window: 2010-01-01 through 2025-01-01 exclusive.
- Signal: positive 126-session price return; select up to two ETFs.
- Timing: completed-close signal, next-session close execution, then close-to-close return.
- Risk: 12% annualized volatility target, 20-session covariance lookback, 50% single-name cap.
- Cost: 6 bps per unit of one-way turnover; excludes spread, market impact, tax, and fund expenses.
- SHA-256 of aligned close panel: `2e2e2c2e7e1d3578dc645740191d72fbfd3d42a5726bf985e89d7a276c7490b8`.
- Provider data can be revised; exact results may change when downloaded again.
- This is an illustrative historical research case, not a validated live strategy or a return forecast.
