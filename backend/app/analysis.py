"""Educational indicator calculations and a deliberately simple, lagged backtest."""
from __future__ import annotations

from math import isfinite


def ema_series(values: list[float], period: int) -> list[float | None]:
    if period < 1:
        raise ValueError("period must be positive")
    if len(values) < period:
        return [None] * len(values)
    alpha = 2.0 / (period + 1.0)
    result: list[float | None] = [None] * (period - 1)
    current = sum(values[:period]) / period
    result.append(current)
    for value in values[period:]:
        current = alpha * value + (1.0 - alpha) * current
        result.append(current)
    return result


def rsi_value(values: list[float], period: int = 14) -> float | None:
    """Wilder RSI using the first-period average followed by Wilder smoothing."""
    if period < 1:
        raise ValueError("period must be positive")
    if len(values) <= period:
        return None
    changes = [values[i] - values[i - 1] for i in range(1, len(values))]
    avg_gain = sum(max(change, 0.0) for change in changes[:period]) / period
    avg_loss = sum(max(-change, 0.0) for change in changes[:period]) / period
    for change in changes[period:]:
        avg_gain = ((period - 1) * avg_gain + max(change, 0.0)) / period
        avg_loss = ((period - 1) * avg_loss + max(-change, 0.0)) / period
    if avg_loss == 0:
        return 50.0 if avg_gain == 0 else 100.0
    return round(100.0 - 100.0 / (1.0 + avg_gain / avg_loss), 2)


def analyze_closes(values: list[float]) -> dict:
    if any(not isfinite(v) or v <= 0 for v in values):
        raise ValueError("close prices must be finite positive numbers")
    e9 = ema_series(values, 9)[-1] if values else None
    e21 = ema_series(values, 21)[-1] if values else None
    rsi = rsi_value(values)
    if e9 is None or e21 is None:
        trend = "INSUFFICIENT_DATA"
    elif e9 > e21:
        trend = "EMA9_ABOVE_EMA21"
    elif e9 < e21:
        trend = "EMA9_BELOW_EMA21"
    else:
        trend = "EMA_EQUAL"
    if rsi is None:
        momentum = "INSUFFICIENT_DATA"
    elif rsi >= 70:
        momentum = "HIGHER_MOMENTUM_ZONE"
    elif rsi <= 30:
        momentum = "LOWER_MOMENTUM_ZONE"
    else:
        momentum = "MIDDLE_ZONE"
    return {
        "observations": len(values),
        "ema_9": round(e9, 4) if e9 is not None else None,
        "ema_21": round(e21, 4) if e21 is not None else None,
        "rsi_14": rsi,
        "trend_context": trend,
        "momentum_context": momentum,
        "is_trade_signal": False,
        "disclaimer": "Educational indicator context only; not a forecast or trade instruction.",
    }


def ema_crossover_backtest(values: list[float], fee_bps: float = 5.0) -> dict:
    """Long/flat EMA crossover toy test; decisions are lagged one full bar."""
    if len(values) < 30:
        raise ValueError("at least 30 closing prices are required")
    if any(not isfinite(v) or v <= 0 for v in values):
        raise ValueError("close prices must be finite positive numbers")
    if not isfinite(fee_bps) or fee_bps < 0 or fee_bps > 100:
        raise ValueError("fee_bps must be between 0 and 100")

    e9 = ema_series(values, 9)
    e21 = ema_series(values, 21)
    signals = [0] * len(values)
    for i in range(len(values)):
        if e9[i] is not None and e21[i] is not None and e9[i] > e21[i]:
            signals[i] = 1

    fee = fee_bps / 10000.0
    strategy_returns: list[float] = []
    benchmark_returns: list[float] = []
    turnover_events = 0
    previous_position = 0
    for i in range(1, len(values)):
        held_position = signals[i - 1]  # only use information available at prior close
        change = abs(held_position - previous_position)
        if change:
            turnover_events += 1
        market_return = values[i] / values[i - 1] - 1.0
        strategy_returns.append(held_position * market_return - change * fee)
        benchmark_returns.append(market_return)
        previous_position = held_position

    def summarize(returns: list[float]) -> dict:
        equity = 1.0
        peak = 1.0
        max_drawdown = 0.0
        for ret in returns:
            equity *= 1.0 + ret
            peak = max(peak, equity)
            if peak:
                max_drawdown = max(max_drawdown, (peak - equity) / peak)
        active = [r for r in returns if r != 0]
        wins = sum(1 for r in active if r > 0)
        return {
            "total_return_pct": round((equity - 1.0) * 100.0, 3),
            "max_drawdown_pct": round(max_drawdown * 100.0, 3),
            "positive_period_pct": round((wins / len(active)) * 100.0, 2) if active else None,
        }

    return {
        "strategy": "EMA9/EMA21 long-or-flat; next-bar close-to-close simulation",
        "observations": len(values),
        "fee_per_side_bps": fee_bps,
        "position_changes": turnover_events,
        "strategy_result": summarize(strategy_returns),
        "buy_and_hold_reference": summarize(benchmark_returns),
        "lookahead_control": "Signal from bar t is applied only to return from t to t+1.",
        "is_investment_advice": False,
        "disclaimer": "Historical toy simulation only. It excludes slippage, taxes, liquidity limits and corporate actions; results do not predict future performance.",
    }
