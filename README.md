# FastAPI backend

Install: `pip install -r requirements.txt`

Run: `uvicorn app.main:app --host 0.0.0.0 --port 8000`

Tests: `python -m pytest -q`

Interactive API docs: `http://127.0.0.1:8000/docs`

Example indicator request:

```json
{"close_prices":[100,101,100.5,102,103,102.5,104,105,104.5,106,107,106.5,108,109,110,109,111,112,113,112,114,115,116]}
```

Example backtest request requires at least 30 prices:

```json
{"close_prices":[100,101,102,101,103,104,103,105,106,105,107,108,109,108,110,111,112,111,113,114,115,114,116,117,118,117,119,120,121,120],"fee_bps":5}
```

All endpoints are educational/research only. There are no live broker connections or order execution routes.
