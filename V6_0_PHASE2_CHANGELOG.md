# NIFTY AI TRADER PRO — V6.0 Phase 2

## Implemented
1. Strict historical OHLCV structure validation:
   - required timestamp/open/high/low/close/volume fields
   - timezone-aware ISO-8601 timestamps
   - strictly increasing timestamps; duplicates and out-of-order rows rejected
   - finite positive OHLC prices, non-negative volume
   - OHLC candle geometry validation
   - optional expected-interval gap reporting (missing rows are never fabricated)
   - explicit `source_authenticity=NOT_VERIFIED` and `licensing_status=NOT_VERIFIED`
2. Expanding-window walk-forward research:
   - EMA9/EMA21 descriptive baseline
   - each prediction uses only information available through the current candle
   - outcome scored against the following candle
   - directional accuracy, coverage and confusion counts
   - no execution simulation or trade instructions
3. New API endpoints:
   - `POST /api/analysis/validate-dataset`
   - `POST /api/research/walk-forward`
4. Added regression tests.

## Important limitations
- A structurally valid file is not proof of authentic NSE data.
- Synthetic samples are not evidence of market accuracy.
- No connected/verified historical provider, news, options open interest or market breadth is claimed.
- Walk-forward metrics on a user-supplied dataset are descriptive research, not a guarantee of future results.
- `real_orders_enabled=false`; `paper_only=true`.

## Versioning
Backend remains V6.0.0. This is Phase 2 of the V6.0 backend foundation. Android UI and APK integration have not been performed in this phase.
