from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_is_paper_only():
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["real_orders_enabled"] is False
    assert r.json()["virtual_capital"] == 500000

def test_v5_integration_status_is_read_only():
    r = client.get("/api/v5/integration-status")
    assert r.status_code == 200
    body = r.json()
    assert body["real_orders_enabled"] is False
    assert body["live_data_verified"] is False


def test_angel_one_placeholder_is_not_connected():
    r = client.get("/api/providers/angel-one")
    assert r.status_code == 200
    assert r.json()["connected"] is False

def test_market_does_not_claim_live_data():
    r = client.get("/api/market")
    assert r.json()["value"] is None

def test_paper_order():
    r = client.post("/api/paper/order", json={"side":"BUY","quantity":1,"reference_price":100})
    assert r.status_code == 200
    assert r.json()["status"] == "SIMULATED_ONLY"


def test_indicator_analysis_is_not_trade_signal():
    prices = [100 + i * 0.4 for i in range(30)]
    r = client.post("/api/analysis/indicators", json={"close_prices": prices})
    assert r.status_code == 200
    assert r.json()["is_trade_signal"] is False
    assert r.json()["ema_9"] is not None


def test_backtest_requires_enough_data_and_lags_signals():
    prices = [100 + i * 0.2 for i in range(40)]
    r = client.post("/api/backtest/ema-crossover", json={"close_prices": prices})
    assert r.status_code == 200
    assert "bar t" in r.json()["lookahead_control"]
    assert r.json()["is_investment_advice"] is False


def test_rsi_uses_wilder_smoothing():
    from app.analysis import rsi_value
    # 15 consecutive gains: Wilder RSI must be 100, including its zero-loss edge case.
    assert rsi_value([100 + i for i in range(15)], 14) == 100.0
    # Flat prices have no gains or losses and are defined as neutral RSI 50.
    assert rsi_value([100.0] * 15, 14) == 50.0



def test_nse_status_reports_informational_mode(monkeypatch):
    async def fake_discover():
        return {"provider": "NSE public MCP", "mode": "EDUCATIONAL_INFORMATIONAL",
                "delay": "approximately 1–3 minutes", "real_time_trading": False,
                "commercial_use": False, "tools": {"cm_market": []}}
    monkeypatch.setattr("app.main.discover_tools", fake_discover)
    r = client.get("/api/nse/status")
    assert r.status_code == 200
    assert r.json()["provider"] == "NSE public MCP"
    assert r.json()["real_time_trading"] is False

def test_nse_query_rejects_non_allowlisted_tool():
    r = client.post("/api/nse/query", json={"server": "cm_market",
        "tool": "place_order", "arguments": {}})
    assert r.status_code == 400

def test_nse_query_validates_server():
    r = client.post("/api/nse/query", json={"server": "unknown",
        "tool": "get_market_breadth", "arguments": {}})
    assert r.status_code == 503 or r.status_code == 400

def test_advanced_market_context_is_descriptive_only():
    highs = [101 + i * 0.5 for i in range(60)]
    lows = [99 + i * 0.5 for i in range(60)]
    closes = [100 + i * 0.5 for i in range(60)]
    r = client.post("/api/analysis/market-context", json={"high": highs, "low": lows, "close": closes})
    assert r.status_code == 200
    body = r.json()
    assert body["is_trade_signal"] is False
    assert body["ema_50"] is not None
    assert body["macd"] is not None
    assert body["recent_range_reference"]["support_zone_reference"] is not None
    assert body["news_sentiment"] == "NOT_CONNECTED"


def test_advanced_context_rejects_invalid_candles():
    r = client.post("/api/analysis/market-context", json={"high": [99, 100], "low": [101, 99], "close": [100, 99]})
    assert r.status_code == 400

def test_provider_status_never_claims_unconfigured_feed_is_live():
    body = client.get("/api/providers/status").json()
    assert body["connected"] is False
    assert body["mode"] == "OFFLINE_NOT_CONFIGURED"
    assert body["read_only"] is True
    assert body["real_orders_enabled"] is False


def test_advanced_context_calculates_vwap_only_with_volume():
    highs = [102.0, 103.0, 104.0]
    lows = [100.0, 101.0, 102.0]
    closes = [101.0, 102.0, 103.0]
    no_volume = client.post("/api/analysis/market-context", json={"high": highs, "low": lows, "close": closes})
    assert no_volume.status_code == 200
    assert no_volume.json()["vwap"] is None
    with_volume = client.post("/api/analysis/market-context", json={"high": highs, "low": lows, "close": closes, "volume": [10, 20, 30]})
    assert with_volume.status_code == 200
    assert with_volume.json()["vwap"] is not None
    assert with_volume.json()["data_basis"] == "CALLER_SUPPLIED_HISTORICAL_OHLCV"


def test_advanced_context_rejects_mismatched_volume():
    r = client.post("/api/analysis/market-context", json={"high": [102, 103], "low": [100, 101], "close": [101, 102], "volume": [10]})
    assert r.status_code == 400


def test_historical_csv_endpoint_validates_and_analyzes_ohlcv():
    rows = ["Date,Open,High,Low,Close,Volume"]
    for i in range(60):
        close = 100 + i * 0.25
        rows.append(f"2026-01-{(i%28)+1:02d}T00:{i//28:02d}:00,{close-0.2},{close+1},{close-1},{close},1000")
    # Use monotonically increasing ISO timestamps for deterministic validation.
    rows = ["Date,Open,High,Low,Close,Volume"] + [
        f"2026-01-01T00:{i:02d}:00,{100+i*.25:.2f},{101+i*.25:.2f},{99+i*.25:.2f},{100+i*.25:.2f},1000" for i in range(60)
    ]
    response = client.post("/api/analysis/csv", content="\n".join(rows), headers={"content-type": "text/csv"})
    assert response.status_code == 200
    body = response.json()
    assert body["data_quality"]["rows"] == 60
    assert body["ema_50"] is not None
    assert body["macd_signal_9"] is not None
    assert body["vwap"] is not None
    assert body["is_trade_signal"] is False


def test_historical_csv_rejects_bad_ohlc_and_nonascending_dates():
    bad_ohlc = "Date,Open,High,Low,Close,Volume\n2026-01-01,100,99,98,100,10\n2026-01-02,100,102,99,101,10"
    r = client.post("/api/analysis/csv", content=bad_ohlc, headers={"content-type": "text/csv"})
    assert r.status_code == 400
    bad_dates = "Date,Open,High,Low,Close,Volume\n2026-01-02,100,102,99,101,10\n2026-01-01,101,103,100,102,10"
    r = client.post("/api/analysis/csv", content=bad_dates, headers={"content-type": "text/csv"})
    assert r.status_code == 400


def test_current_integration_status_is_explicitly_offline():
    r = client.get("/api/v5/integration-status")
    assert r.status_code == 200
    body = r.json()
    assert body["app_version"] == "6.0.0"
    assert body["live_data_verified"] is False
    assert body["real_orders_enabled"] is False
    assert body["angel_one"]["connected"] is False

def test_news_sentiment_provider_is_not_configured():
    r = client.get("/api/news-sentiment/status")
    assert r.status_code == 200
    assert r.json()["connected"] is False

def test_normalized_market_event_validation():
    r = client.post("/api/market/validate-event", json={
        "symbol": "NIFTY", "last_price": 22000,
        "exchange_timestamp": "2026-11-18T09:15:00+05:30"
    })
    assert r.status_code == 200
    assert r.json()["valid"] is True
    assert r.json()["read_only"] is True
    assert "not a connected live feed" in r.json()["note"]

def test_market_event_rejects_invalid_price():
    r = client.post("/api/market/validate-event", json={
        "symbol": "NIFTY", "last_price": -1,
        "exchange_timestamp": "2026-11-18T09:15:00+05:30"
    })
    assert r.status_code == 400


def test_latest_market_endpoint_is_explicitly_offline_without_provider_events():
    r = client.get("/api/market/latest")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "OFFLINE_NO_EVENTS"
    assert body["events"] == {}
    assert body["read_only"] is True
    assert body["real_orders_enabled"] is False


def test_market_stream_rejects_out_of_order_events():
    import asyncio
    from datetime import datetime, timedelta, timezone
    from app.providers.contracts import parse_tick
    from app.providers.stream_manager import MarketStreamManager

    manager = MarketStreamManager()
    now = datetime.now(timezone.utc)
    newer = parse_tick({"symbol": "NIFTY", "last_price": 22010,
                        "exchange_timestamp": now.isoformat()}, "TEST", received_at=now)
    older = parse_tick({"symbol": "NIFTY", "last_price": 22000,
                        "exchange_timestamp": (now - timedelta(seconds=1)).isoformat()}, "TEST", received_at=now)
    assert asyncio.run(manager.publish(newer)) is True
    assert asyncio.run(manager.publish(older)) is False
    snapshot = manager.latest_snapshot("NIFTY")
    assert snapshot["events"]["NIFTY"]["last_price"] == 22010


def test_market_tick_rejects_far_future_exchange_timestamp():
    from datetime import datetime, timedelta, timezone
    from app.providers.contracts import parse_tick
    future = datetime.now(timezone.utc) + timedelta(minutes=3)
    try:
        parse_tick({"symbol": "NIFTY", "last_price": 22000,
                    "exchange_timestamp": future.isoformat()}, "TEST")
        assert False, "future timestamp should be rejected"
    except ValueError as exc:
        assert "future" in str(exc)


def test_simulation_snapshot_is_synthetic_and_paper_only():
    response = client.get("/api/simulation/snapshot")
    assert response.status_code == 200
    body = response.json()
    assert body["symbol"] == "NIFTY"
    assert body["data_type"] == "SYNTHETIC_NOT_MARKET_DATA"
    assert body["read_only"] is True
    assert body["real_orders_enabled"] is False


def test_simulation_historical_sample_is_synthetic_and_has_ohlcv():
    response = client.get("/api/simulation/historical-sample?count=80")
    assert response.status_code == 200
    body = response.json()
    assert body["data_type"] == "SYNTHETIC_NOT_HISTORICAL_MARKET_DATA"
    assert len(body["candles"]) == 80
    assert all({"open", "high", "low", "close", "volume"} <= set(c) for c in body["candles"])
    assert body["real_orders_enabled"] is False


def test_simulation_historical_sample_rejects_invalid_count():
    response = client.get("/api/simulation/historical-sample?count=10")
    assert response.status_code == 400


def test_v6_research_endpoints_accept_synthetic_integration_sample():
    sample = client.get("/api/simulation/historical-sample?count=80")
    assert sample.status_code == 200
    body = sample.json()
    assert body["data_type"] == "SYNTHETIC_NOT_HISTORICAL_MARKET_DATA"
    candles = body["candles"]
    payload = {
        "high": [c["high"] for c in candles],
        "low": [c["low"] for c in candles],
        "close": [c["close"] for c in candles],
        "volume": [c["volume"] for c in candles],
    }
    assert client.post("/api/analysis/market-context", json=payload).status_code == 200
    multi = client.post("/api/analysis/multi-factor", json=payload)
    assert multi.status_code == 200
    assert multi.json()["paper_only"] is True
    rows = [{
        "timestamp": c["date"], "open": c["open"], "high": c["high"],
        "low": c["low"], "close": c["close"], "volume": c["volume"]
    } for c in candles]
    validation = client.post("/api/analysis/validate-dataset", json={"rows": rows, "interval_seconds": 300})
    assert validation.status_code == 200
    assert validation.json()["valid"] is True
    walk = client.post("/api/research/walk-forward", json={"close_prices": payload["close"], "min_history": 30})
    assert walk.status_code == 200
    assert walk.json()["is_trade_signal"] is False
