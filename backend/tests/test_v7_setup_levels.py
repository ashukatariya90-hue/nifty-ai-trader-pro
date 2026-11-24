import math
from fastapi.testclient import TestClient
from app.main import app
from app.setup_levels import build_setup_levels

client = TestClient(app)

def candles(n=80, direction=1):
    close = [25000 + direction*i*3 + math.sin(i/4)*2 for i in range(n)]
    high = [x+5 for x in close]
    low = [x-5 for x in close]
    vol = [1000+(i%5)*100 for i in range(n)]
    return high, low, close, vol

def test_bullish_context_has_all_hypothetical_levels():
    h,l,c,v = candles()
    result = build_setup_levels(h,l,c,v)
    assert result['market_context'] == 'BULLISH_CONTEXT'
    setup = result['hypothetical_setup']
    assert setup['entry_zone'] is not None
    assert setup['retracement_zone'] is not None
    assert setup['stop_loss_invalidation'] is not None
    assert [x['name'] for x in setup['targets']] == ['T1','T2','T3']
    assert result['paper_only'] is True and result['real_orders_enabled'] is False

def test_mixed_context_does_not_force_setup():
    h,l,c,v = candles(direction=0)
    result = build_setup_levels(h,l,c,v)
    assert result['signal_state'] == 'NO_SETUP'
    assert result['hypothetical_setup']['entry_zone'] is None
    assert result['hypothetical_setup']['stop_loss_invalidation'] is None

def test_api_returns_paper_only_setup_levels():
    h,l,c,v = candles()
    response = client.post('/api/v7/analysis/setup-levels', json={'high':h,'low':l,'close':c,'volume':v})
    assert response.status_code == 200
    body = response.json()
    assert body['engine'] == 'V7_SETUP_LEVELS_ALPHA'
    assert body['real_orders_enabled'] is False

def test_api_rejects_short_history():
    h,l,c,v = candles(n=20)
    response = client.post('/api/v7/analysis/setup-levels', json={'high':h,'low':l,'close':c,'volume':v})
    assert response.status_code == 400
