<div align="center">

<img src="assets/etf-compass-banner.svg" alt="ETF Compass — 系统化 ETF 策略与 AI 研究" width="100%">

# ETF Compass 🧭

### 系统化策略 + AI 研究，构建自己的 ETF Trading Agent

**让策略发现轮动机会，让 AI 补充研究与质疑，帮助你做出更有依据的 ETF 投资决策。**

一个开放、可扩展的 ETF 研究框架，组合多策略信号、ETF 轮动、动态仓位与 AI 多角色研究，支持你持续加入自己的策略、数据和模型。

[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-35A16B.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/Tests-pytest-6A5ACD.svg)](#测试)

[快速开始](#快速开始) · [策略与 AI](#策略与-ai-如何配合) · [公开研究案例](#可复现研究案例) · [English](#english-overview)

</div>

ETF Compass 面向希望用系统化方法研究 ETF 的投资者与开发者。规则策略负责计算信号、筛选标的、形成组合并控制仓位；AI 研究补充市场证据、检验不同观点、提示风险。两者各自发挥优势，为投资决策提供更完整的参考。项目提供可扩展的 Python 组件，方便你按自己的方法继续 DIY。

## 策略与 AI 如何配合

- **系统化策略寻找机会：** 趋势突破、动量、均值回归等信号参与 ETF 评分与轮动，持仓缓冲降低排名小幅变化带来的频繁切换。
- **组合管理关注风险：** 根据历史波动估算仓位，应用单 ETF 权重与组合总敞口限制，并在限制后重新复核风险预算。
- **AI 研究补充判断：** 多角色工作流整理依据、检验多空观点、复核风险并形成结构化评估；AI 观点与策略权重分开，供使用者综合判断。

策略与 AI 结合的目标，是把可重复执行的投资纪律与更广泛的研究视角放在同一决策流程中，帮助使用者评估机会和风险；历史表现不代表未来收益。

## 工作流程

```mermaid
%%{init: {"theme":"base", "themeVariables":{"primaryColor":"#eee9f7","primaryTextColor":"#332b45","primaryBorderColor":"#8875aa","lineColor":"#77628f","secondaryColor":"#f4f0f8","tertiaryColor":"#faf8fc","clusterBkg":"#f8f5fb","clusterBorder":"#c9bdd8"}}}%%
flowchart TB
    M["行情与研究事实"]
    subgraph S["系统化组合策略"]
        direction LR
        S1["信号与 ETF 排名"] --> S2["轮动与持仓缓冲"] --> S3["风险预算与仓位"]
    end
    subgraph A["AI 独立研究"]
        direction LR
        A1["多角色研究"] --> A2["证据与观点检验"] --> A3["组合风险复核"]
    end
    S --> R["投资决策参考"]
    A --> R
    M --> S
    M --> A
    classDef input fill:#f0ebf6,stroke:#8875aa,color:#332b45,stroke-width:1.5px
    classDef strategy fill:#e8e1f1,stroke:#77628f,color:#332b45,stroke-width:1.5px
    classDef research fill:#f1edf7,stroke:#8875aa,color:#332b45,stroke-width:1.5px
    classDef output fill:#ddd3ea,stroke:#67547d,color:#2c2439,stroke-width:2px
    class M input
    class S1,S2,S3 strategy
    class A1,A2,A3 research
    class R output
```

行情与研究资料由使用者接入，并应覆盖决策时点可获得的信息。策略形成组合计划，AI 独立研究并给出评估，最终判断由使用者完成。

## 快速开始

需要 Python 3.11 或更新版本。离线示例使用固定随机种子的合成价格，安装后即可运行并看到回测摘要：

```bash
git clone https://github.com/BZX667/ETF-Compass.git
cd ETF-Compass
python -m pip install -e '.[dev]'
python examples/quickstart.py
```

这是软件运行示例，不是市场数据结果。项目目前没有通用命令行程序或内置行情源；使用真实市场数据请接入自己的数据，并确认数据与信号时点一致。

## 可复现研究案例

公开案例使用五只美国上市 ETF 的复权日线数据，固定研究区间为 2010–2024 年：按过去 126 个交易日的正动量评分，最多选择两只 ETF，以此前 20 日估算风险，模拟信号日之后的下一交易日收盘成交，并按单边换手计入 6 个基点成本。

```bash
python -m pip install -e '.[research]'
python examples/public_research_case.py
```

[案例报告](examples/results/public-etf-research-case.md)展示该样本中轮动策略与 SPY 的对比，并记录研究假设、数据区间和价格面板哈希。价格通过 [yfinance](https://ranaroussi.github.io/yfinance/reference/api/yfinance.download.html) 获取自 [Yahoo Finance](https://finance.yahoo.com/quote/SPY/history/)。数据可能被供应方修订，结果可能变化；这是一项历史研究示例，不是收益承诺，也未验证 A 股、QDII 或盘中执行。

## 按需扩展，打造自己的 ETF Agent

ETF Compass 提供可组合的策略、组合管理、AI 研究和报告模块。你可以加入自己的因子与 ETF 范围，调整筛选、轮动和风险方法，接入偏好的行情源与模型，逐步构建适合自己的 ETF Trading Agent。

## 日报与周复盘

项目包含日报与周度复盘渲染，以及邮件和微信渠道推送函数，便于把组合计划、AI 评估与阶段性结果纳入日常研究流程。行情接入、模型服务配置、账户账本与定时任务由集成应用负责。

<div align="center">
  <a href="assets/report-preview.svg"><img src="assets/report-preview.svg" alt="ETF Compass 日报样式示例，内容与数值均为虚构" width="72%"></a>
  <br>
  <sub>日报样式预览 · 虚构示例 · <a href="assets/report-preview.svg">查看大图</a></sub>
</div>

## 测试

```bash
python -m pip install -e '.[dev]'
pytest
```

测试覆盖信号、组合约束、回测执行时序与成本、报告、推送和 AI 工作流输出校验。

## 项目范围

ETF Compass 是 ETF 研究与策略开发框架，不是券商或投资顾问，也不保证收益。回测结果受到数据质量、标的范围、评估区间、交易成本和执行假设影响；用于实盘前，应结合真实市场规则独立验证。

## English overview

ETF Compass is an open, extensible framework for building an AI-powered ETF trading agent. Systematic signals rank and rotate ETFs, portfolio controls size positions, and independent AI research adds evidence and risk review. Bring your own market data, strategies, and model provider to shape the workflow around your approach. It is a research toolkit, not a promise of investment returns.
