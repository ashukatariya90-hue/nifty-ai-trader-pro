from datetime import datetime, timezone
from uuid import uuid4


class PaperLedger:
    """In-memory educational ledger. It never connects to a broker or routes orders."""

    def __init__(self, initial_balance=500000, fee_bps=10, max_order_notional_fraction=0.20):
        if initial_balance <= 0:
            raise ValueError("initial_balance must be positive")
        if fee_bps < 0 or fee_bps > 1000:
            raise ValueError("fee_bps must be between 0 and 1000")
        if not 0 < max_order_notional_fraction <= 1:
            raise ValueError("max_order_notional_fraction must be in (0, 1]")
        self.initial_balance = float(initial_balance)
        self.fee_bps = float(fee_bps)
        self.max_order_notional = self.initial_balance * max_order_notional_fraction
        self.cash = float(initial_balance)
        self.orders = []
        self.positions = {}
        self.fills = []
        self.realized_pnl = 0.0
        self._client_order_ids = {}

    @staticmethod
    def _now():
        return datetime.now(timezone.utc).isoformat()

    def submit(self, side, quantity, reference_price, symbol="NIFTY", client_order_id=None):
        side = str(side).upper()
        symbol = str(symbol).upper().strip()
        if side not in {"BUY", "SELL"}:
            raise ValueError("side must be BUY or SELL")
        if not symbol or len(symbol) > 40:
            raise ValueError("symbol must contain 1 to 40 characters")
        if isinstance(quantity, bool) or int(quantity) != quantity or quantity <= 0 or quantity > 100000:
            raise ValueError("quantity must be a positive integer no greater than 100000")
        if reference_price <= 0:
            raise ValueError("reference_price must be positive")
        notional = int(quantity) * float(reference_price)
        if notional > self.max_order_notional:
            raise ValueError("order exceeds configured paper notional limit")
        if client_order_id:
            client_order_id = str(client_order_id).strip()
            if len(client_order_id) > 80:
                raise ValueError("client_order_id must be at most 80 characters")
            existing_id = self._client_order_ids.get(client_order_id)
            if existing_id:
                return self._get_order(existing_id)
        order = {
            "order_id": str(uuid4()), "client_order_id": client_order_id,
            "symbol": symbol, "side": side, "quantity": int(quantity),
            "reference_price": float(reference_price), "status": "ACCEPTED",
            "created_at": self._now(), "updated_at": self._now(),
            "filled_quantity": 0, "average_fill_price": None,
            "fees": 0.0, "message": "Accepted for paper simulation only."
        }
        self.orders.append(order)
        if client_order_id:
            self._client_order_ids[client_order_id] = order["order_id"]
        return dict(order)

    def _get_order(self, order_id):
        for order in self.orders:
            if order["order_id"] == order_id:
                return order
        raise KeyError("paper order not found")

    def fill(self, order_id, fill_price=None):
        order = self._get_order(order_id)
        if order["status"] != "ACCEPTED":
            raise ValueError("only ACCEPTED paper orders can be filled")
        price = float(fill_price if fill_price is not None else order["reference_price"])
        if price <= 0:
            raise ValueError("fill_price must be positive")
        qty, symbol, side = order["quantity"], order["symbol"], order["side"]
        gross = qty * price
        fee = gross * self.fee_bps / 10000.0
        position = self.positions.get(symbol, {"quantity": 0, "average_price": 0.0})
        if side == "BUY":
            if gross + fee > self.cash + 1e-9:
                raise ValueError("insufficient virtual cash for fill including fees")
            new_qty = position["quantity"] + qty
            # Include the entry fee in cost basis so realized P&L later
            # accounts for both entry-side and exit-side fees.
            avg = ((position["quantity"] * position["average_price"]) + gross + fee) / new_qty
            self.cash -= gross + fee
            position = {"quantity": new_qty, "average_price": avg}
        else:
            if qty > position["quantity"]:
                raise ValueError("insufficient paper position quantity to sell")
            self.cash += gross - fee
            self.realized_pnl += (price - position["average_price"]) * qty - fee
            new_qty = position["quantity"] - qty
            position = {"quantity": new_qty, "average_price": position["average_price"] if new_qty else 0.0}
        self.positions[symbol] = position
        order.update({
            "status": "FILLED", "filled_quantity": qty,
            "average_fill_price": price, "fees": round(fee, 2),
            "updated_at": self._now(), "message": "Filled in paper ledger; no broker order was sent."
        })
        self.fills.append({
            "fill_id": str(uuid4()), "order_id": order_id, "symbol": symbol,
            "side": side, "quantity": qty, "price": price,
            "gross_value": round(gross, 2), "fees": round(fee, 2),
            "timestamp": self._now(), "classification": "SIMULATED_PAPER_FILL"
        })
        return dict(order)

    def cancel(self, order_id):
        order = self._get_order(order_id)
        if order["status"] != "ACCEPTED":
            raise ValueError("only ACCEPTED paper orders can be cancelled")
        order.update({"status": "CANCELLED", "updated_at": self._now(),
                      "message": "Cancelled in paper ledger; no broker order was sent."})
        return dict(order)

    def record(self, side, quantity, reference_price):
        """Legacy endpoint compatibility: immediate simulated fill."""
        order = self.submit(side, quantity, reference_price)
        if order["status"] == "ACCEPTED":
            self.fill(order["order_id"])
        order = self._get_order(order["order_id"])
        result = dict(order)
        result["status"] = "SIMULATED_ONLY"
        return result

    def snapshot(self):
        return {
            "mode": "PAPER_ONLY", "classification": "SIMULATED_NOT_BROKER_EXECUTION",
            "initial_virtual_balance": self.initial_balance,
            "virtual_balance": round(self.cash, 2),
            "available_cash": round(self.cash, 2),
            "realized_pnl": round(self.realized_pnl, 2),
            "fee_bps": self.fee_bps, "max_order_notional": round(self.max_order_notional, 2),
            "positions": {k: dict(v) for k, v in self.positions.items() if v["quantity"] != 0},
            "orders": [dict(o) for o in self.orders],
            "fills": [dict(f) for f in self.fills],
            "real_orders_enabled": False
        }
