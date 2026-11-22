"""Chronological walk-forward evaluation of a transparent EMA context baseline.

At each observation, only closes through that observation are used. The
resulting label is compared with the next bar's direction. This is a research
diagnostic, not a trading strategy, forecast guarantee, or investment advice.
"""
from __future__ import annotations

from math import isfinite
from .analysis import ema_series


def evaluate_walk_forward(closes: list[float], min_history: int = 30) -> dict:
    if not isinstance(closes, list) or min_history < 22 or len(closes) <= min_history:
        raise ValueError("closes must exceed min_history, which must be at least 22")
    if any(not isfinite(float(x)) or float(x) <= 0 for x in closes):
        raise ValueError("closes must contain finite positive numbers")

    counts = {"up_correct": 0, "up_incorrect": 0, "down_correct": 0,
              "down_incorrect": 0, "flat_actual": 0, "neutral_prediction": 0}
    evaluated = 0
    covered = 0

    # At t, classify using closes[0:t+1], then score against t -> t+1.
    for t in range(min_history - 1, len(closes) - 1):
        history = closes[:t + 1]
        fast = ema_series(history, 9)[-1]
        slow = ema_series(history, 21)[-1]
        if fast is None or slow is None or fast == slow:
            counts["neutral_prediction"] += 1
            continue
        predicted = 1 if fast > slow else -1
        actual_change = closes[t + 1] / closes[t] - 1.0
        actual = 1 if actual_change > 0 else -1 if actual_change < 0 else 0
        evaluated += 1
        covered += 1
        if actual == 0:
            counts["flat_actual"] += 1
        elif predicted == actual and actual > 0:
            counts["up_correct"] += 1
        elif predicted == actual and actual < 0:
            counts["down_correct"] += 1
        elif predicted > 0:
            counts["up_incorrect"] += 1
        else:
            counts["down_incorrect"] += 1

    correct = counts["up_correct"] + counts["down_correct"]
    directional_actual = evaluated - counts["flat_actual"]
    return {
        "evaluation": "EXPANDING_WINDOW_NEXT_BAR_DIRECTION_CLASSIFICATION",
        "observations": len(closes),
        "min_history": min_history,
        "out_of_sample_predictions": evaluated,
        "coverage_pct": round(covered / max(1, len(closes) - min_history) * 100.0, 2),
        "directional_accuracy_pct": round(correct / directional_actual * 100.0, 2) if directional_actual else None,
        "confusion_counts": counts,
        "lookahead_control": "Each prediction uses data through t only; outcome is the subsequent t-to-t+1 move.",
        "data_provenance": "CALLER_SUPPLIED_NOT_AUTHENTICATED",
        "limitations": [
            "A structurally valid dataset is not proof of authentic exchange data.",
            "Synthetic data must not be used to claim real-market accuracy.",
            "No fees, slippage, liquidity, market impact or execution are simulated.",
            "Results are descriptive research metrics and do not imply future performance."
        ],
        "classification": "EDUCATIONAL_RESEARCH_ONLY",
        "is_trade_signal": False,
        "real_orders_enabled": False,
        "paper_only": True,
    }
