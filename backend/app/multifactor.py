"""Transparent multi-factor descriptive engine for educational paper research.

This module deliberately does not emit BUY/SELL instructions or a predictive
probability. Scores describe agreement among supplied historical OHLCV factors.
Missing data is reported as unavailable rather than imputed.
"""
from __future__ import annotations

from math import isfinite
from .analysis import ema_series, rsi_value


def analyze_factors(high: list[float], low: list[float], close: list[float],
                    volume: list[float] | None = None) -> dict:
    n = len(close)
    if not (len(high) == len(low) == n) or n < 50:
        raise ValueError("at least 50 aligned OHLC candles are required")
    for name, values in (("high", high), ("low", low), ("close", close)):
        if any(not isfinite(float(v)) or float(v) <= 0 for v in values):
            raise ValueError(f"{name} must contain finite positive values")
    if any(l > h or c < l or c > h for h, l, c in zip(high, low, close)):
        raise ValueError("candles must satisfy low <= close <= high")
    if volume is not None and (len(volume) != n or any(not isfinite(float(v)) or v < 0 for v in volume)):
        raise ValueError("volume must align with candles and be finite and non-negative")

    e9, e21, e50 = (ema_series(close, p)[-1] for p in (9, 21, 50))
    trend_state = "MIXED"
    trend_score = 0
    if e9 is not None and e21 is not None and e50 is not None:
        if e9 > e21 > e50:
            trend_state, trend_score = "UPWARD_ALIGNMENT", 1
        elif e9 < e21 < e50:
            trend_state, trend_score = "DOWNWARD_ALIGNMENT", -1

    rsi = rsi_value(close, 14)
    momentum_state = "NEUTRAL_OR_UNAVAILABLE"
    momentum_score = 0
    if rsi is not None:
        if rsi >= 55:
            momentum_state, momentum_score = "POSITIVE_MOMENTUM_CONTEXT", 1
        elif rsi <= 45:
            momentum_state, momentum_score = "NEGATIVE_MOMENTUM_CONTEXT", -1
        else:
            momentum_state = "MID_RANGE_MOMENTUM"

    returns = [(close[i] / close[i-1]) - 1 for i in range(1, n)]
    recent_vol = sum(abs(x) for x in returns[-14:]) / min(14, len(returns))
    prior_vol = sum(abs(x) for x in returns[-42:-14]) / 28 if len(returns) >= 42 else None
    if prior_vol is None or prior_vol == 0:
        volatility_state = "INSUFFICIENT_COMPARISON"
    elif recent_vol > prior_vol * 1.5:
        volatility_state = "VOLATILITY_EXPANDING"
    elif recent_vol < prior_vol * 0.67:
        volatility_state = "VOLATILITY_CONTRACTING"
    else:
        volatility_state = "VOLATILITY_STABLE"

    volume_state = "UNAVAILABLE"
    volume_ratio = None
    volume_score = 0
    if volume is not None and len(volume) >= 20:
        baseline = sum(volume[-20:-1]) / 19
        volume_ratio = (volume[-1] / baseline) if baseline > 0 else None
        if volume_ratio is not None:
            volume_state = "ABOVE_RECENT_AVERAGE" if volume_ratio >= 1.25 else "BELOW_RECENT_AVERAGE" if volume_ratio <= 0.75 else "NEAR_RECENT_AVERAGE"

    components = [
        {"factor": "trend", "state": trend_state, "score": trend_score, "available": True},
        {"factor": "momentum", "state": momentum_state, "score": momentum_score, "available": rsi is not None},
        {"factor": "volatility", "state": volatility_state, "score": None, "available": prior_vol is not None},
        {"factor": "volume", "state": volume_state, "score": volume_score if volume is not None else None, "available": volume is not None},
        {"factor": "news", "state": "NOT_CONNECTED", "score": None, "available": False},
        {"factor": "options_open_interest", "state": "NOT_CONNECTED", "score": None, "available": False},
        {"factor": "market_breadth", "state": "NOT_CONNECTED", "score": None, "available": False},
    ]
    directional = [trend_score, momentum_score]
    net = sum(directional)
    if net == 2:
        agreement = "INDICATORS_AGREE_POSITIVE"
    elif net == -2:
        agreement = "INDICATORS_AGREE_NEGATIVE"
    elif net == 0:
        agreement = "MIXED_OR_NEUTRAL"
    else:
        agreement = "PARTIAL_ALIGNMENT"
    return {
        "engine": "V6_MULTI_FACTOR_FOUNDATION",
        "classification": "DESCRIPTIVE_HISTORICAL_CONTEXT_ONLY",
        "observations": n,
        "data_quality": {"valid_ohlc": True, "volume_available": volume is not None,
                         "minimum_history_met": True, "source_timestamp": "NOT_SUPPLIED",
                         "source_identity": "CALLER_SUPPLIED", "freshness": "UNVERIFIED"},
        "factors": components,
        "factor_agreement": agreement,
        "directional_context_score": net,
        "directional_context_score_range": [-2, 2],
        "metrics": {"ema_9": round(e9, 4), "ema_21": round(e21, 4),
                    "ema_50": round(e50, 4), "rsi_14": rsi,
                    "recent_mean_absolute_return_14": round(recent_vol, 8),
                    "prior_mean_absolute_return_28": round(prior_vol, 8) if prior_vol is not None else None,
                    "volume_last_vs_prior_19_ratio": round(volume_ratio, 4) if volume_ratio is not None else None},
        "limitations": ["No verified live or licensed historical feed is connected.",
                        "News, options open interest and market breadth are unavailable.",
                        "No predictive probability or trade instruction is produced.",
                        "Synthetic or caller-supplied candles cannot validate real-market performance."],
        "real_orders_enabled": False,
        "paper_only": True
    }
