import math
import pytest
from app.multifactor import analyze_factors


def series(n=80, trend=1.0):
    close = [25000 + trend * i * 2 + math.sin(i / 3) * 5 for i in range(n)]
    high = [x + 4 for x in close]
    low = [x - 4 for x in close]
    volume = [1000 + (i % 7) * 50 for i in range(n)]
    return high, low, close, volume


def test_multifactor_returns_descriptive_output_only():
    h, l, c, v = series()
    result = analyze_factors(h, l, c, v)
    assert result["engine"] == "V6_MULTI_FACTOR_FOUNDATION"
    assert result["observations"] == 80
    assert result["paper_only"] is True
    assert result["real_orders_enabled"] is False
    assert "trade" not in result


def test_missing_optional_factors_are_not_invented():
    h, l, c, _ = series()
    result = analyze_factors(h, l, c)
    states = {x["factor"]: x["state"] for x in result["factors"]}
    assert states["news"] == "NOT_CONNECTED"
    assert states["options_open_interest"] == "NOT_CONNECTED"
    assert states["market_breadth"] == "NOT_CONNECTED"
    assert states["volume"] == "UNAVAILABLE"


def test_requires_minimum_history():
    h, l, c, v = series(30)
    with pytest.raises(ValueError):
        analyze_factors(h, l, c, v)


def test_rejects_misaligned_volume():
    h, l, c, v = series()
    with pytest.raises(ValueError):
        analyze_factors(h, l, c, v[:-1])


def test_rejects_invalid_candle_geometry():
    h, l, c, v = series()
    h[10] = l[10] - 1
    with pytest.raises(ValueError):
        analyze_factors(h, l, c, v)
