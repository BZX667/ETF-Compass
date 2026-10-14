<div align="center">

<img src="assets/etf-compass-banner.svg" alt="ETF Compass — systematic ETF strategies and AI research" width="100%">

### 让策略保持纪律，让 AI 分析拓展视角

**ETF Compass 是一个面向 ETF 研究的开源 Python 工具包，将系统化策略、组合风险控制与 AI 独立研究组合在一起。**

[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-35A16B.svg)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Research%20Prototype-E9A23B.svg)](#项目状态)

[English](#english) · [快速开始](#快速开始) · [报告与推送](#报告与推送)

</div>

规则信号负责候选筛选、ETF 轮动与仓位约束；AI 根据调用方提供的市场事实补充证据、检验多空观点并提示风险。策略结果保持可复核，AI 提供独立研究视角；AI 不改写策略权重，也不执行交易。

## 工作流程

```mermaid
flowchart TB
    INPUT([最新可用行情与市场事实<br/>由调用方接入])

    subgraph STRATEGY[系统化策略 · 规则与仓位]
        direction LR
        S1[价格信号<br/>趋势 · 动量 · 均值回归 · 突破]
        S2[信号合议与 ETF 轮动<br/>Top-K · 持仓缓冲]
        S3[仓位与风险控制<br/>目标波动率 · 敞口上限]
        S4[目标组合计划]
        S1 --> S2 --> S3 --> S4
    end

    subgraph RESEARCH[AI 研究 · 证据与风险]
        direction LR
        A1[多源事实分析<br/>技术 · 资金 · 产业]
        A2[多空观点检验]
        A3[风险复核与总结]
        A4[独立评估<br/>立场 · 证据 · 观察项]
        A1 --> A2 --> A3 --> A4
    end

    INPUT --> STRATEGY
    INPUT --> RESEARCH
    STRATEGY --> OUTPUT([日报与每周复盘])
    RESEARCH --> OUTPUT
```

AI 以同一组行情与市场事实为输入，并把策略计划作为评估背景；它提供独立观点与风险审视，不覆盖策略信号。

## 系统化策略 + AI 分析

| 策略 | 核心思路 |
| --- | --- |
| 海龟通道突破 | 跟踪价格突破近期区间及趋势退出信号 |
| 标准化动量 | 衡量相对强度，并按波动水平标准化 |
| 双动量 | 比较资产间强弱，并过滤绝对动量为负的标的 |
| RSI 均值回归 | 识别短期超卖状态与潜在修复信号 |
| ATR 波动率突破 | 结合均线和真实波幅跟踪趋势变化 |

信号可等权合议，用于横截面排名与 Top-K 轮动；持仓缓冲减少排名边缘的频繁切换。仓位模块基于历史波动估算风险目标，并限制单项权重和组合总敞口。调用方提供行情数据，信号应使用决策时点可获得的信息，并按实际执行时点评估。

AI 工作流包含事实分析、多空研究、风险审查和组合经理总结，输出立场、信心、证据、风险与观察项。调用方可选择兼容 API 或本地模型接入。项目思路与 [TradingAgents](https://github.com/TauricResearch/TradingAgents) 相关。

### 按需扩展，自己 DIY

核心组件是可单独调用、自由组合的 Python 函数，方便从现有模块出发，逐步搭建自己的 ETF 研究流程：

- **添加策略信号：** 自定义函数返回按日期和 ETF 对齐的 `pandas.DataFrame`，即可传入 `equal_weight_ensemble({...})`，与内置信号共同合议。
- **定制筛选与仓位：** `select_assets(...)` 根据评分和持仓缓冲选出候选 ETF；`volatility_target_weights(...)` 根据历史收益估算目标权重，并应用波动率与敞口限制。可按需替换任一环节，接入自己的筛选、轮动、仓位或风险方法。
- **扩展 AI 研究：** `run_trading_agents_review(...)` 接收自定义 `facts` 事实组、`complete(prompt)` 模型适配器和 `rounds` 讨论轮数（1–5）。事实组名称可定义分析角色，适配器可连接兼容 API 或本地模型。内置多空、风险与总结阶段提供开箱即用的流程；也可复用模型适配接口，自行编排分析步骤。

不同扩展都可接回组合和报告流程。验证时应统一数据时点、基准、评估周期与执行假设。

## 报告与推送

支持生成并推送每日策略简报与每周复盘。日报呈现行情、策略组合和 AI 研究摘要；周报整理调用方提供的轮动回顾，以及仅包含已到期样本的 AI 观点评估。报告用于辅助研究，不替代策略验证。

<div align="center">
  <a href="assets/report-preview.svg">
    <img src="assets/report-preview.svg" alt="ETF Compass 每日策略简报样式预览；示例数据为虚构内容" width="78%">
  </a>
  <br>
  <sub>每日简报样式预览 · 点击图片查看原图 · 所有数值均为虚构示例</sub>
</div>

HTML 日报可用于邮件或浏览器查看；微信渠道发送适配的文本版。报告中的行情、账户信息与推送渠道由使用者的部署应用提供；本仓库不包含私人账户数据或推送密钥。

## 快速开始

需要 Python 3.11 或更高版本：

```bash
git clone https://github.com/BZX667/ETF-Compass.git
cd ETF-Compass
python -m pip install -e '.[dev]'
python -m pytest
```

以下是应用侧集成示意。策略函数接收调用方准备的行情面板，不直接连接行情供应商：

```python
from etf_compass import (
    equal_weight_ensemble, momentum_score, render_daily_report,
    render_daily_report_html, select_assets, send_report,
    volatility_target_weights, turtle_breakout,
)
from etf_compass.agents import run_trading_agents_review

# my_signal(close) 由应用侧实现，返回与内置信号对齐的 DataFrame。
signals = {
    "momentum": momentum_score(close),
    "turtle": turtle_breakout(close),
    "my_signal": my_signal(close),
}
scores = equal_weight_ensemble(signals).iloc[-1].dropna()
selected = select_assets(scores, top_k=4, held=current_holdings, buffer_multiple=1.25)
weights = volatility_target_weights(returns, selected, max_weight=0.35)

review = run_trading_agents_review(
    facts={"technical": technical_facts, "industry": industry_facts},
    mechanical_plan=f"Target weights: {weights.to_dict()}",
    complete=my_model_adapter,  # 由调用方接入兼容 API 或本地模型
)
report_inputs = dict(
    as_of=report_date,
    market_data_as_of=quote_timestamp,
    rotation=[
        {"symbol": symbol, "score": scores[symbol], "weight": weights[symbol]}
        for symbol in selected
    ],
    assessment=review.assessment,
    market_coverage="selected ETF universe",
)
text_report = render_daily_report(**report_inputs)
html_report = render_daily_report_html(**report_inputs)
send_report("ETF daily research", text_report, html_body=html_report, channels=("email", "serverchan"))
```

周复盘可使用 `ForwardObservation` 保存每次观点的观察日、评估结束日、立场、标的收益和基准收益，再调用 `score_forward_observations(..., as_of=review_date)` 与 `render_weekly_review(...)`。收益区间必须从观察日之后开始，并统一基准和持有期；仅已结束的样本进入评分。

## 项目状态与风险说明

ETF Compass 处于研究原型阶段。它不提供交易执行，也不保证收益。数据质量、幸存者偏差、评估窗口、交易成本和执行时点都会影响结果；应独立验证策略和 AI 输出，不把历史表现视为未来保证。本项目不构成投资建议。

---

<a id="english"></a>

## English

**ETF Compass is an open-source Python toolkit for ETF research, combining systematic rotation and risk controls with AI-assisted analysis.** It includes daily and weekly report helpers, with optional email and WeChat delivery. Market data, model access, credentials, and scheduling are supplied by the deploying application; no personal keys, account details, or trading records are included. The project is a research prototype and does not execute trades or provide investment advice.
