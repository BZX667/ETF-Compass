import json

import numpy as np
import pandas as pd
import pytest

from etf_compass import select_assets, volatility_target_weights
from etf_compass.evaluation import build_assessment_prompt, parse_assessment


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


def test_assessment_prompt_keeps_llm_advisory():
    prompt = build_assessment_prompt("facts", "mechanical plan")
    assert "do not issue orders" in prompt
    assert "do not override" in prompt


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
