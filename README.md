# ETF Compass

![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)
![Research prototype](https://img.shields.io/badge/status-research%20prototype-orange)
![License: MIT](https://img.shields.io/badge/license-MIT-green)

**A modular ETF investment research agent: systematic rotation, explicit risk controls, and independent LLM evaluation.**

ETF Compass is a small, auditable Python toolkit for building ETF research workflows. Rules-based selection and portfolio sizing stay in control of the mechanical plan. An optional LLM assessment adds a separate view of supplied market evidence; it cannot change the plan or place trades.

> Research software only. It does not provide investment advice, guarantee returns, connect to a brokerage, or place orders. Backtests and model opinions can be wrong.

## What is included

- **Rotation selection** with a configurable top-K universe and incumbent hold buffer.
- **Volatility-aware sizing** with per-asset and total-exposure limits.
- **Provider-neutral LLM assessment** with a constrained prompt and validated JSON schema.
- **No account integration**: callers provide the market data and decide how to store results.

```text
Caller-provided market data ──> Scores ──> Rotation ──> Risk-limited weights
             │                                      │
             └────────> Independent LLM review <────┘
                       (advisory; cannot override)
```

## Install

Requires Python 3.11 or newer.

```bash
python -m pip install -e '.[dev]'
```

## Example

```python
import pandas as pd

from etf_compass import select_assets, volatility_target_weights
from etf_compass.evaluation import build_assessment_prompt, parse_assessment

# Scores are computed by your own strategy from point-in-time data.
scores = pd.Series({"ETF_A": 0.9, "ETF_B": 0.7, "ETF_C": 0.5})
selected = select_assets(scores, top_k=2, held=["ETF_B"], buffer_multiple=1.5)

# Supply historical returns ending before the intended execution period.
returns = pd.DataFrame(
    {
        "ETF_A": [0.010, -0.004, 0.006, 0.002] * 5,
        "ETF_B": [0.003, 0.005, -0.002, 0.004] * 5,
        "ETF_C": [-0.006, 0.002, 0.001, 0.003] * 5,
    }
)
weights = volatility_target_weights(
    returns,
    selected,
    target_volatility=0.15,
    lookback=20,
    max_weight=0.35,
)

prompt = build_assessment_prompt(
    market_facts="Describe only verified market facts here.",
    mechanical_plan=f"Selected assets: {selected}",
)
# Send `prompt` through a provider you configure, then validate its response:
# assessment = parse_assessment(provider.complete(prompt))
```

## Design boundaries

- Scores, data sourcing, execution timing, and portfolio policy belong to the caller.
- Risk estimates use historical returns supplied by the caller. Pass observations strictly before the execution period to avoid look-ahead leakage.
- LLM output is a separate, untrusted assessment. It is not an alpha claim, order, or substitute for backtesting.
- The package has no broker integration and stores no account, holding, or trade data.

## Development

```bash
python -m pytest
```

ETF Compass is an early-stage project. APIs may change while the core interfaces and validation improve.

## 风险说明

本项目用于技术研究，不构成证券投资建议或收益承诺。市场有风险，策略和模型输出均可能产生损失；使用者应独立验证数据、回测和执行假设。
