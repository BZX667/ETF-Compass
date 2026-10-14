"""Rule-based cross-sectional selection helpers."""

from __future__ import annotations

import math
from collections.abc import Iterable

import pandas as pd


def select_assets(
    scores: pd.Series,
    *,
    top_k: int,
    held: Iterable[str] = (),
    buffer_multiple: float = 1.0,
) -> list[str]:
    """Select the highest-ranked assets while applying a hold buffer.

    New positions must rank in the top ``top_k``. Existing positions are kept
    while they remain within ``ceil(top_k * buffer_multiple)``. The returned
    list never exceeds ``top_k`` and is ordered by descending score.

    Scores should be computed only from information available at the decision
    time. This function does not fetch data or generate a score.
    """
    if top_k < 1:
        raise ValueError("top_k must be at least 1")
    if buffer_multiple < 1.0 or not math.isfinite(buffer_multiple):
        raise ValueError("buffer_multiple must be finite and at least 1")
    if not scores.index.is_unique:
        raise ValueError("scores must have unique asset identifiers")

    ranked = scores.dropna().sort_values(ascending=False, kind="stable")
    names = ranked.index.tolist()
    rank = {name: i + 1 for i, name in enumerate(names)}
    keep_rank = math.ceil(top_k * buffer_multiple)
    held_set = set(held)
    incumbents = [name for name in names if name in held_set and rank[name] <= keep_rank]
    entrants = [name for name in names if rank[name] <= top_k and name not in incumbents]

    chosen = incumbents[:top_k]
    chosen.extend(name for name in entrants if len(chosen) < top_k)
    return sorted(chosen, key=lambda name: rank[name])
