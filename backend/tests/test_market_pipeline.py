import asyncio
from datetime import datetime, timedelta, timezone

from backend.app.providers.contracts import parse_tick
from backend.app.providers.stream_manager import MarketStreamManager


def make_tick(price=25000, seconds_old=0):
    now = datetime.now(timezone.utc)
    exchange_time = now - timedelta(seconds=seconds_old)

    return parse_tick(
        {
            "symbol": "NIFTY",
            "last_price": price,
            "exchange_timestamp": exchange_time.isoformat(),
        },
        source="SIMULATED_TEST",
        received_at=now,
    )


def test_valid_tick_is_parsed():
    tick = make_tick()

    assert tick.symbol == "NIFTY"
    assert tick.last_price == 25000
    assert tick.data_classification == "SYNTHETIC_NOT_MARKET_DATA"


def test_invalid_price_is_rejected():
    try:
        parse_tick(
            {
                "symbol": "NIFTY",
                "last_price": -1,
                "exchange_timestamp": datetime.now(timezone.utc).isoformat(),
            },
            source="SIMULATED_TEST",
        )
    except ValueError:
        return

    raise AssertionError("Invalid price was not rejected")


def test_stale_event_is_rejected():
    async def run():
        manager = MarketStreamManager()
        tick = make_tick(seconds_old=120)

        accepted = await manager.publish(tick)

        assert accepted is False
        assert manager.status()["metrics"]["rejected_stale_events"] == 1

    asyncio.run(run())


def test_out_of_order_event_is_rejected():
    async def run():
        manager = MarketStreamManager()
        first = make_tick(price=25000)

        second = parse_tick(
            {
                "symbol": "NIFTY",
                "last_price": 24990,
                "exchange_timestamp": (
                    first.exchange_timestamp - timedelta(seconds=1)
                ).isoformat(),
            },
            source="SIMULATED_TEST",
        )

        assert await manager.publish(first) is True
        assert await manager.publish(second) is False

        metrics = manager.status()["metrics"]
        assert metrics["accepted_events"] == 1
        assert metrics["rejected_out_of_order_events"] == 1

    asyncio.run(run())


def test_websocket_receives_simulated_event():
    class FakeWebSocket:
        def __init__(self):
            self.messages = []

        async def accept(self):
            pass

        async def send_json(self, payload):
            self.messages.append(payload)

    async def run():
        manager = MarketStreamManager()
        client = FakeWebSocket()

        await manager.connect(client)
        accepted = await manager.publish(make_tick())

        assert accepted is True
        assert len(client.messages) == 1
        assert client.messages[0]["symbol"] == "NIFTY"
        assert client.messages[0]["read_only"] is True
        assert client.messages[0]["real_orders_enabled"] is False

        await manager.disconnect(client)

    asyncio.run(run())
