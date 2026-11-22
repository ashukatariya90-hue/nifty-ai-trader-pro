from datetime import datetime, timedelta, timezone
import math
import pytest

from app.historical_validation import validate_ohlcv_rows
from app.walk_forward import evaluate_walk_forward


def rows(n=5, step=60):
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    result = []
    for i in range(n):
        c = 25000 + i * 2
        result.append({
            "timestamp": (start + timedelta(seconds=i * step)).isoformat(),
            "open": c - 1, "high": c + 2, "low": c - 2,
            "close": c, "volume": 1000 + i,
        })
    return result


def test_validates_timezone_aware_chronological_ohlcv():
    result = validate_ohlcv_rows(rows(), interval_seconds=60)
    assert result["valid"] is True
    assert result["rows"] == 5
    assert result["gap_count"] == 0
    assert result["source_authenticity"] == "NOT_VERIFIED"
    assert result["paper_only"] is True


def test_reports_missing_intervals_without_filling_them():
    data = rows()
    data[3]["timestamp"] = (datetime.fromisoformat(data[3]["timestamp"]) + timedelta(seconds=120)).isoformat()
    data[4]["timestamp"] = (datetime.fromisoformat(data[4]["timestamp"]) + timedelta(seconds=120)).isoformat()
    result = validate_ohlcv_rows(data, interval_seconds=60)
    assert result["gap_count"] == 1
    assert result["gaps"][0]["estimated_missing_intervals"] == 2


@pytest.mark.parametrize("mutator, message", [
    (lambda x: x[2].update(timestamp="2026-01-01T00:00:00"), "timezone"),
    (lambda x: x[2].update(close=float("nan")), "finite"),
    (lambda x: x[2].update(high=1), "geometry"),
    (lambda x: x[2].update(volume=-1), "volume"),
    (lambda x: x[2].update(timestamp=x[1]["timestamp"]), "duplicate"),
    (lambda x: x[2].update(timestamp=x[0]["timestamp"]), "increasing"),
])
def test_rejects_invalid_dataset(mutator, message):
    data = rows()
    mutator(data)
    with pytest.raises(ValueError, match=message):
        validate_ohlcv_rows(data)


def test_walk_forward_is_chronological_and_paper_only():
    closes = [25000 + i * 2 + math.sin(i / 3) * 4 for i in range(100)]
    result = evaluate_walk_forward(closes, min_history=30)
    assert result["out_of_sample_predictions"] > 0
    assert "t-to-t+1" in result["lookahead_control"]
    assert result["is_trade_signal"] is False
    assert result["real_orders_enabled"] is False
    assert result["paper_only"] is True


def test_walk_forward_rejects_invalid_or_short_series():
    with pytest.raises(ValueError):
        evaluate_walk_forward([1, 2, 3])
    with pytest.raises(ValueError):
        evaluate_walk_forward([1.0] * 40 + [float("inf")])


def csv_text(n=80, date_only=False):
    lines = ["Date,Open,High,Low,Close,Volume"]
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    for i in range(n):
        close = 25000 + i * 1.5 + math.sin(i / 4) * 8
        stamp = (start + timedelta(days=i)).date().isoformat() if date_only else (start + timedelta(minutes=5 * i)).isoformat()
        lines.append(f"{stamp},{close-1:.4f},{close+2:.4f},{close-2:.4f},{close:.4f},{1000+i}")
    return "\n".join(lines)


def test_v61_csv_pipeline_runs_validation_factors_and_walk_forward():
    from app.historical_research import analyze_historical_csv
    result = analyze_historical_csv(csv_text())
    assert result["engine"] == "V6_3_NSE_NATIVE_CSV_RESEARCH"
    assert result["rows"] == 80
    assert result["dataset_validation"]["valid"] is True
    assert result["multi_factor"]["observations"] == 80
    assert result["walk_forward"]["out_of_sample_predictions"] > 0
    assert result["source_authenticity"] == "NOT_VERIFIED"
    assert result["paper_only"] is True
    assert result["real_orders_enabled"] is False


def test_v61_csv_pipeline_accepts_date_only_daily_rows_without_inventing_time():
    from app.historical_research import analyze_historical_csv
    result = analyze_historical_csv(csv_text(date_only=True))
    assert result["date_only_rows_normalized_to_utc_midnight"] == 80
    assert "UTC midnight" in result["limitations"][1]


def test_v61_csv_pipeline_rejects_short_or_bad_timestamp_data():
    from app.historical_research import analyze_historical_csv
    with pytest.raises(ValueError, match="at least 50"):
        analyze_historical_csv(csv_text(49))
    bad = csv_text().replace("2026-01-01T00:05:00+00:00", "2026-01-01T00:05:00", 1)
    with pytest.raises(ValueError, match="timezone"):
        analyze_historical_csv(bad)
