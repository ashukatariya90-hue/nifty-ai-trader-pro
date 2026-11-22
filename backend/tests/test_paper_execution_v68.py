from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_paper_order_lifecycle_and_accounting():
    created = client.post("/api/paper/orders", json={
        "side": "BUY", "quantity": 2, "reference_price": 100,
        "symbol": "V68TEST", "client_order_id": "lifecycle-test-buy"
    })
    assert created.status_code == 200
    order = created.json()
    assert order["status"] == "ACCEPTED"
    order_id = order["order_id"]

    filled = client.post(f"/api/paper/orders/{order_id}/fill", json={"fill_price": 101})
    assert filled.status_code == 200
    assert filled.json()["status"] == "FILLED"

    ledger = client.get("/api/paper/ledger").json()
    assert ledger["classification"] == "SIMULATED_NOT_BROKER_EXECUTION"
    assert ledger["positions"]["V68TEST"]["quantity"] == 2
    assert ledger["virtual_balance"] < 500000
    assert ledger["fills"][-1]["classification"] == "SIMULATED_PAPER_FILL"
    assert ledger["real_orders_enabled"] is False


def test_paper_sell_requires_existing_position():
    created = client.post("/api/paper/orders", json={
        "side": "SELL", "quantity": 1, "reference_price": 100,
        "symbol": "NOHOLDING"
    }).json()
    response = client.post(f"/api/paper/orders/{created['order_id']}/fill", json={})
    assert response.status_code == 400
    assert "insufficient paper position" in response.json()["detail"]


def test_paper_cancel_and_terminal_state():
    created = client.post("/api/paper/orders", json={
        "side": "BUY", "quantity": 1, "reference_price": 100
    }).json()
    order_id = created["order_id"]
    cancelled = client.post(f"/api/paper/orders/{order_id}/cancel")
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "CANCELLED"
    second_cancel = client.post(f"/api/paper/orders/{order_id}/cancel")
    assert second_cancel.status_code == 400


def test_paper_order_idempotency():
    payload = {"side": "BUY", "quantity": 1, "reference_price": 100,
               "client_order_id": "same-client-id"}
    first = client.post("/api/paper/orders", json=payload).json()
    second = client.post("/api/paper/orders", json=payload).json()
    assert first["order_id"] == second["order_id"]


def test_paper_notional_limit_and_no_real_execution():
    response = client.post("/api/paper/orders", json={
        "side": "BUY", "quantity": 1000, "reference_price": 1000
    })
    assert response.status_code == 400
    ledger = client.get("/api/paper/ledger").json()
    assert ledger["real_orders_enabled"] is False
