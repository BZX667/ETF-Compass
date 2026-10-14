import json

import numpy as np
import pandas as pd
import pytest

from etf_compass import (
    render_backtest_report,
    run_rotation_backtest,
    select_assets,
    volatility_target_weights,
)
from etf_compass.agents import run_trading_agents_review
from etf_compass.evaluation import parse_assessment
from etf_compass.signals import (
    dual_momentum_score,
    equal_weight_ensemble,
    mean_reversion_signal,
    momentum_score,
    turtle_breakout,
    volatility_breakout_signal,
    volatility_breakout_signal,
)


def test_rotation_retains_incumbent_inside_buffer_and_fills_top_k():
    scores = pd.Series({"A": 5.0, "B": 4.0, "C": 3.0, "D": 2.0})
    assert select_assets(scores, top_k=2, held=["C"], buffer_multiple=1.5) == ["A", "C"]


def test_rotation_drops_incumbent_outside_buffer():
    scores = pd.Series({"A": 5.0, "B": 4.0, "C": 3.0, "D": 2.0})
    assert select_assets(scores, top_k=2, held=["D"], buffer_multiple=1.5) == ["A", "B"]


def test_volatility_weights_obey_name_and_gross_caps():
    rng = np.random.default_rng(17)
    returns = pd.DataFrame(rng.normal(0, 0.01, (40, 3)), columns=list("ABC"))
    weights = volatility_target_weights(
        returns, list("ABC"), lookback=20, max_weight=0.3, max_gross_exposure=0.8
    )
    assert (weights >= 0).all()
    assert weights.max() <= 0.3 + 1e-12
    assert weights.sum() <= 0.8 + 1e-12


def test_volatility_weights_recheck_risk_after_caps():
    rng = np.random.default_rng(1)
    returns = pd.DataFrame(rng.normal(0, 0.01, (20, 4)), columns=list("ABCD"))
    weights = volatility_target_weights(
        returns,
        list("ABCD"),
        target_volatility=0.08,
        lookback=20,
        max_weight=0.25,
        max_gross_exposure=1.0,
    )
    covariance = returns.cov().to_numpy() * 252
    estimated_volatility = float(np.sqrt(weights.to_numpy() @ covariance @ weights.to_numpy()))
    assert weights.max() <= 0.25 + 1e-12
    assert weights.sum() <= 1.0 + 1e-12
    assert estimated_volatility <= 0.08 + 1e-10


def test_zero_volatility_asset_does_not_receive_redistributed_weight():
    rng = np.random.default_rng(4)
    returns = pd.DataFrame({"A": rng.normal(0, 0.01, 20), "B": 0.0})
    weights = volatility_target_weights(
        returns,
        ["A", "B"],
        target_volatility=0.2,
        lookback=20,
        max_weight=0.3,
        max_gross_exposure=1.0,
    )
    assert weights["A"] == pytest.approx(0.3)
    assert weights["B"] == 0.0


def test_rotation_backtest_uses_next_close_period_and_charges_rebalance_cost():
    dates = pd.RangeIndex(8)
    close = pd.DataFrame(
        {"A": [100, 101, 102, 103, 104, 105, 106, 107], "B": [100, 102, 101, 103, 104, 104, 108, 109]},
        index=dates,
    )
    scores = pd.DataFrame({"A": [1.0] * 8, "B": [0.0] * 8}, index=dates)
    result = run_rotation_backtest(
        close,
        scores,
        benchmark_close=close["B"],
        top_k=1,
        target_volatility=100.0,
        risk_lookback=2,
        max_weight=1.0,
        fee=0.01,
        annualization=4,
    )
    assert result.positions.loc[2, "A"] == pytest.approx(1.0)
    assert result.daily_returns.loc[3] == pytest.approx(-0.01)
    assert result.daily_returns.loc[4] == pytest.approx(104 / 103 - 1)
    assert result.metrics["total_cost"] == pytest.approx(0.01)
    assert result.benchmark_equity is not None
    assert result.benchmark_equity.iloc[0] == pytest.approx(1.0)
    report = render_backtest_report(result)
    assert "Annualized return" in report
    assert "Maximum drawdown" in report


def test_rotation_backtest_preclose_mode_executes_at_same_date_close():
    dates = pd.RangeIndex(7)
    close = pd.DataFrame({"A": [100, 101, 102, 103, 104, 105, 106]}, index=dates)
    scores = pd.DataFrame({"A": [1.0] * 7}, index=dates)
    result = run_rotation_backtest(
        close,
        scores,
        top_k=1,
        target_volatility=100.0,
        risk_lookback=2,
        max_weight=1.0,
        execution_lag=1,
        fee=0.01,
        annualization=4,
    )
    assert result.positions.loc[3, "A"] == pytest.approx(1.0)
    assert result.daily_returns.loc[3] == pytest.approx(-0.01)
    assert result.daily_returns.loc[4] == pytest.approx(104 / 103 - 1)


def test_assessment_parser_validates_fields():
    payload = {
        "stance": "neutral",
        "confidence": "medium",
        "evidence": ["A verified fact"],
        "risks": [],
        "watch_items": ["A condition to monitor"],
    }
    result = parse_assessment(json.dumps(payload))
    assert result.stance == "neutral"
    assert result.evidence == ("A verified fact",)
    payload["stance"] = "buy"
    with pytest.raises(ValueError):
        parse_assessment(json.dumps(payload))


def test_turtle_breakout_uses_prior_bars_and_persists_state():
    close = pd.DataFrame({"ETF_A": [1.0, 2.0, 3.0, 2.0, 2.5, 3.5, 2.9, 2.7, 2.6]})
    signal = turtle_breakout(close, entry_window=3, exit_window=3)
    assert signal["ETF_A"].iloc[:5].eq(0).all()
    assert signal["ETF_A"].iloc[5:8].eq(1).all()
    assert signal["ETF_A"].iloc[8] == 0


def test_equal_weight_ensemble_averages_signal_panels():
    first = pd.DataFrame({"A": [1.0], "B": [-1.0]}, index=[1])
    second = pd.DataFrame({"A": [0.0], "C": [1.0]}, index=[1])
    combined = equal_weight_ensemble({"trend": first, "momentum": second})
    assert combined.loc[1, "A"] == 0.5
    assert combined.loc[1, "B"] == -0.5
    assert combined.loc[1, "C"] == 0.5


def test_trading_agents_runs_analysts_debate_risk_and_final_review():
    prompts = []

    def complete(prompt):
        prompts.append(prompt)
        if "Return only valid JSON" in prompt:
            return json.dumps(
                {
                    "stance": "neutral",
                    "confidence": "low",
                    "evidence": ["limited data"],
                    "risks": ["uncertainty"],
                    "watch_items": ["next update"],
                }
            )
        return "Evidence-based note"

    result = run_trading_agents_review(
        {"technical": "price facts", "industry": "industry facts"},
        "mechanical plan",
        complete,
        rounds=2,
    )
    assert len(result.analyst_notes) == 2
    assert len(result.debate) == 2
    assert result.assessment.stance == "neutral"
    assert len(prompts) == 2 + 2 * 2 + 2
    assert "Round 1 bull" in prompts[4]


def test_price_signal_functions_return_aligned_panels():
    dates = pd.RangeIndex(300)
    close = pd.DataFrame(
        {"A": np.linspace(100, 180, 300), "B": np.linspace(180, 100, 300)},
        index=dates,
    )
    high = close * 1.01
    low = close * 0.99
    momentum = momentum_score(close, norm_window=100)
    dual = dual_momentum_score(close)
    rsi = mean_reversion_signal(close)
    breakout = volatility_breakout_signal(close, high, low)

    for signal in (momentum, dual, rsi, breakout):
        assert signal.index.equals(close.index)
        assert signal.columns.equals(close.columns)
    assert dual.iloc[-1]["A"] > 0
    assert dual.iloc[-1]["B"] == 0
    assert momentum.iloc[-1]["A"] > 0
    assert breakout.dtypes.eq(float).all()


def test_rsi_reversion_enters_oversold_and_exits_after_recovery():
    close = pd.DataFrame({"A": [100, 98, 96, 94, 92, 94, 96, 98, 100, 102]})
    signal = mean_reversion_signal(close, rsi_window=3, oversold=35, exit_rsi=50)
    assert signal["A"].iloc[4] == 1
    assert signal["A"].iloc[-1] == 0


def test_atr_breakout_enters_then_exits_below_ema():
    close = pd.DataFrame({"A": [10.0] * 20 + [20.0, 8.0, 9.0]})
    high = close + 0.5
    low = close - 0.5
    signal = volatility_breakout_signal(
        close, high, low, ema_window=5, atr_window=3, band_multiple=1.0
    )
    assert signal["A"].iloc[20] == 1
    assert signal["A"].iloc[21] == 0
