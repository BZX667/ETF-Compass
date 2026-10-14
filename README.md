<div align="center">

<img src="assets/etf-compass-banner.svg" alt="ETF Compass — systematic ETF strategies and AI research" width="100%">

### 让策略保持纪律，让 AI 分析拓展视角

**ETF Compass 是一个面向 ETF 研究的开源 Python 工具包，将系统化策略、组合风险控制与 AI 独立研究组合在一起。**

[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-35A16B.svg)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Research%20Prototype-E9A23B.svg)](#项目状态)

[English](#english) · [开始使用](#开始使用) · [报告与推送](#报告与推送)

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

### 按需扩展，打造自己的 ETF Agent

ETF Compass 为自主研究和策略开发而设计，提供清晰、可组合的扩展接口。你可以加入自己的量化信号，持续打磨 ETF 筛选与轮动逻辑，定制组合构建和风险控制；也可以接入偏好的模型、补充行情与研究信息，按自己的投资理念拓展 AI 分析。按需组合、逐步演进，打造适合自己的 ETF Trading Agent。

## 报告与推送

内置日报与每周复盘能力，让策略组合、AI 观点和阶段回顾清晰呈现；支持邮件及微信等推送场景，方便将研究结果融入日常工作流。

<div align="center">
  <a href="assets/report-preview.svg">
    <img src="assets/report-preview.svg" alt="ETF Compass 每日策略简报样式预览；示例数据为虚构内容" width="78%">
  </a>
  <br>
  <sub>每日简报样式预览 · 点击图片查看原图 · 所有数值均为虚构示例</sub>
</div>

提供精美的 HTML 日报样式，并支持邮件和微信渠道推送。行情与推送配置由使用者自行接入；公开项目不包含个人账户信息或任何私密密钥。

## 开始使用

需要 Python 3.11 或更高版本。克隆项目并安装，即可开始探索：

```bash
git clone https://github.com/BZX667/ETF-Compass.git
cd ETF-Compass
python -m pip install -e '.[dev]'
```

## 项目状态与风险说明

ETF Compass 处于研究原型阶段。它不提供交易执行，也不保证收益。数据质量、幸存者偏差、评估窗口、交易成本和执行时点都会影响结果；应独立验证策略和 AI 输出，不把历史表现视为未来保证。本项目不构成投资建议。

---

<a id="english"></a>

## English

**ETF Compass is an open-source Python toolkit for ETF research, combining systematic strategies and portfolio risk controls with AI-powered research.** Its modular design invites you to bring your own signals, portfolio ideas, market research, and preferred AI models to build an ETF agent around your approach. Daily briefs and weekly reviews help keep the research process clear and actionable. ETF Compass is a research project and does not execute trades or provide investment advice.
