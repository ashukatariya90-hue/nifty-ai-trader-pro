"""Descriptive, educational market-context metrics. No trade instructions."""
from __future__ import annotations
from math import isfinite, sqrt
from .analysis import ema_series, rsi_value


def _valid(values: list[float], name: str) -> None:
    if len(values) < 2 or any(not isfinite(x) or x <= 0 for x in values):
        raise ValueError(f"{name} must contain at least two finite positive values")


def analyze_market_context(high: list[float], low: list[float], close: list[float], volume: list[float] | None = None) -> dict:
    if not (len(high) == len(low) == len(close)):
        raise ValueError("high, low and close arrays must have equal lengths")
    _valid(close, "close")
    _valid(high, "high")
    _valid(low, "low")
    if any(l > h or c < l or c > h for h, l, c in zip(high, low, close)):
        raise ValueError("each candle must satisfy low <= close <= high")
    if volume is not None and (len(volume) != len(close) or any(not isfinite(v) or v < 0 for v in volume)):
        raise ValueError("volume must match candle count and contain finite non-negative values")

    e9 = ema_series(close, 9)[-1]
    e21 = ema_series(close, 21)[-1]
    e50 = ema_series(close, 50)[-1]
    e12 = ema_series(close, 12)[-1]
    e26 = ema_series(close, 26)[-1]
    macd = (e12 - e26) if e12 is not None and e26 is not None else None
    signal_line = None
    if len(close) >= 34:
        macd_series = []
        fast, slow = ema_series(close, 12), ema_series(close, 26)
        for a, b in zip(fast, slow):
            macd_series.append(a - b if a is not None and b is not None else None)
        valid_macd = [x for x in macd_series if x is not None]
        signal_line = ema_series(valid_macd, 9)[-1] if len(valid_macd) >= 9 else None

    window = min(20, len(close))
    sample = close[-window:]
    mean = sum(sample) / window
    std = sqrt(sum((x - mean) ** 2 for x in sample) / window)
    tr = []
    for i in range(1, len(close)):
        tr.append(max(high[i] - low[i], abs(high[i] - close[i-1]), abs(low[i] - close[i-1])))
    atr14 = sum(tr[-14:]) / min(14, len(tr)) if tr else None

    # Transparent recent-range reference zones, not predictive levels.
    support = min(low[-window:])
    resistance = max(high[-window:])
    trend = "INSUFFICIENT_HISTORY"
    if e9 is not None and e21 is not None:
        trend = "EMA9_ABOVE_EMA21" if e9 > e21 else "EMA9_BELOW_EMA21" if e9 < e21 else "EMA_EQUAL"
    rsi = rsi_value(close)
    vwap = None
    if volume is not None and sum(volume) > 0:
        total_volume = sum(volume)
        vwap = sum(((h + l + c) / 3.0) * v for h, l, c, v in zip(high, low, close, volume)) / total_volume
    return {
        "observations": len(close),
        "trend_context": trend,
        "ema_9": round(e9, 4) if e9 is not None else None,
        "ema_21": round(e21, 4) if e21 is not None else None,
        "ema_50": round(e50, 4) if e50 is not None else None,
        "rsi_14": rsi,
        "macd": round(macd, 5) if macd is not None else None,
        "macd_signal_9": round(signal_line, 5) if signal_line is not None else None,
        "macd_histogram": round(macd - signal_line, 5) if macd is not None and signal_line is not None else None,
        "bollinger_20": {"middle": round(mean, 4), "upper_2sd": round(mean + 2*std, 4), "lower_2sd": round(mean - 2*std, 4)},
        "atr_14": round(atr14, 4) if atr14 is not None else None,
        "vwap": round(vwap, 4) if vwap is not None else None,
        "recent_range_reference": {"lookback_candles": window, "support_zone_reference": round(support, 4), "resistance_zone_reference": round(resistance, 4)},
        "volume_available": volume is not None,
        "data_basis": "CALLER_SUPPLIED_HISTORICAL_OHLCV",
        "news_sentiment": "NOT_CONNECTED",
        "market_breadth": "NOT_CONNECTED",
        "options_sentiment": "NOT_CONNECTED",
        "classification": "DESCRIPTIVE_CONTEXT_ONLY",
        "is_trade_signal": False,
        "disclaimer": "Historical/caller-supplied candle context only. Support/resistance are recent-range references, not forecasts. No BUY/SELL instruction. News, breadth and options fields remain unavailable until an authorized source is configured."
    }
