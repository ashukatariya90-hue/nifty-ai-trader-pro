from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_is_paper_only():
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["real_orders_enabled"] is False
    assert r.json()["virtual_capital"] == 500000

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
