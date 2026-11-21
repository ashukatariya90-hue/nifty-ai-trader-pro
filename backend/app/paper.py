from datetime import datetime, timezone

class PaperLedger:
    def __init__(self, initial_balance=500000):
        if initial_balance <= 0:
            raise ValueError("initial_balance must be positive")
        self.initial_balance = float(initial_balance)
        self.orders = []

    def record(self, side, quantity, reference_price):
        side = side.upper()
        if side not in {"BUY", "SELL"}:
            raise ValueError("side must be BUY or SELL")
        if quantity <= 0 or reference_price <= 0:
            raise ValueError("quantity and reference_price must be positive")
        order = {
            "side": side, "quantity": quantity,
            "reference_price": float(reference_price),
            "status": "SIMULATED_ONLY",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        self.orders.append(order)
        return order

    def snapshot(self):
        return {
            "mode": "PAPER_ONLY",
            "initial_virtual_balance": self.initial_balance,
            "virtual_balance": self.initial_balance,
            "orders": list(self.orders)
        }
