def ema(values, period):
    if period <= 0:
        raise ValueError("period must be positive")
    if len(values) < period:
        return None
    alpha = 2 / (period + 1)
    result = float(values[0])
    for value in values[1:]:
        result = alpha * float(value) + (1 - alpha) * result
    return round(result, 4)

def rsi(values, period=14):
    if period <= 0:
        raise ValueError("period must be positive")
    if len(values) <= period:
        return None
    changes = [float(values[i]) - float(values[i-1]) for i in range(1, len(values))]
    gains = [max(x, 0) for x in changes[-period:]]
    losses = [max(-x, 0) for x in changes[-period:]]
    avg_gain, avg_loss = sum(gains)/period, sum(losses)/period
    if avg_loss == 0:
        return 100.0 if avg_gain > 0 else 50.0
    return round(100 - 100/(1 + avg_gain/avg_loss), 2)

def vwap(prices, volumes):
    if not prices or len(prices) != len(volumes):
        return None
    total = sum(float(v) for v in volumes)
    if total <= 0:
        return None
    return round(sum(float(p)*float(v) for p, v in zip(prices, volumes))/total, 4)
