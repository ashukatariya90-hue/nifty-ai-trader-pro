"""V7 educational setup-level mapper for historical/synthetic OHLCV.

Outputs descriptive, hypothetical levels for paper research only. It does not
recommend trades, estimate guaranteed outcomes, or connect to a broker.
"""
from __future__ import annotations
from math import isfinite
from .analysis import ema_series, rsi_value


def build_setup_levels(high: list[float], low: list[float], close: list[float],
                       volume: list[float] | None = None) -> dict:
    n = len(close)
    if n < 50 or len(high) != n or len(low) != n:
        raise ValueError("at least 50 aligned OHLC candles are required")
    for name, values in (("high", high), ("low", low), ("close", close)):
        if any(not isfinite(float(v)) or float(v) <= 0 for v in values):
            raise ValueError(f"{name} must contain finite positive values")
    if any(l > h or c < l or c > h for h, l, c in zip(high, low, close)):
        raise ValueError("candles must satisfy low <= close <= high")
    if volume is not None and (len(volume) != n or any(not isfinite(float(v)) or v < 0 for v in volume)):
        raise ValueError("volume must align with candles and be finite and non-negative")

    e9, e21, e50 = (ema_series(close, p)[-1] for p in (9, 21, 50))
    rsi = rsi_value(close, 14)
    true_ranges = [max(high[i]-low[i], abs(high[i]-close[i-1]), abs(low[i]-close[i-1])) for i in range(1,n)]
    atr = sum(true_ranges[-14:]) / min(14, len(true_ranges))
    last = float(close[-1])
    lookback = min(20, n-1)
    support = min(float(x) for x in low[-lookback-1:-1])
    resistance = max(float(x) for x in high[-lookback-1:-1])

    if e9 > e21 > e50 and rsi is not None and rsi >= 50:
        bias = "BULLISH_CONTEXT"
    elif e9 < e21 < e50 and rsi is not None and rsi <= 50:
        bias = "BEARISH_CONTEXT"
    else:
        bias = "MIXED_OR_NEUTRAL"

    # Levels are hypothetical references, not entry recommendations.
    if bias == "BULLISH_CONTEXT":
        invalidation = min(support, last - atr)
        risk = max(last - invalidation, atr * 0.5)
        entry = {"lower": round(last, 2), "upper": round(last + atr * 0.15, 2)}
        retracement = {"lower": round(max(invalidation, e21 - atr*0.25), 2),
                       "upper": round(max(invalidation, e21 + atr*0.25), 2)}
        targets = [last + risk, last + 1.5*risk, last + 2*risk]
    elif bias == "BEARISH_CONTEXT":
        invalidation = max(resistance, last + atr)
        risk = max(invalidation - last, atr * 0.5)
        entry = {"lower": round(last - atr * 0.15, 2), "upper": round(last, 2)}
        retracement = {"lower": round(min(invalidation, e21 - atr*0.25), 2),
                       "upper": round(min(invalidation, e21 + atr*0.25), 2)}
        targets = [last - risk, last - 1.5*risk, last - 2*risk]
    else:
        invalidation = None
        risk = None
        entry = None
        retracement = None
        targets = []

    # The status is intentionally non-actionable: confirmation is not inferred
    # from a single candle close or synthetic data.
    return {
        "engine": "V7_SETUP_LEVELS_ALPHA",
        "classification": "HYPOTHETICAL_LEVELS_FOR_HISTORICAL_OR_SYNTHETIC_PAPER_RESEARCH",
        "observations": n,
        "market_context": bias,
        "last_close": round(last, 2),
        "indicators": {"ema_9": round(e9, 4), "ema_21": round(e21, 4),
                       "ema_50": round(e50, 4), "rsi_14": rsi, "atr_14": round(atr, 4)},
        "reference_levels": {"recent_support": round(support, 2), "recent_resistance": round(resistance, 2)},
        "hypothetical_setup": {
            "entry_zone": entry,
            "retracement_zone": retracement,
            "stop_loss_invalidation": round(invalidation, 2) if invalidation is not None else None,
            "targets": [{"name": f"T{i+1}", "price": round(p, 2)} for i,p in enumerate(targets)],
            "risk_distance": round(risk, 2) if risk is not None else None,
            "exit_conditions": ["setup invalidation level breached", "opposing trend alignment confirmed", "signal data becomes stale"],
            "trailing_stop": "Not activated; requires separately validated paper strategy rules"
        },
        "signal_state": "RESEARCH_CONTEXT_ONLY" if bias != "MIXED_OR_NEUTRAL" else "NO_SETUP",
        "data_quality": {"volume_available": volume is not None, "timestamp_supplied": False,
                         "source_verified": False, "freshness": "UNVERIFIED"},
        "paper_only": True,
        "real_orders_enabled": False,
        "limitations": ["Levels are mechanical references, not predictive guarantees.",
                        "No live feed or licensed source is verified by this endpoint.",
                        "Targets and stop levels require out-of-sample validation before UI promotion."]
    }
