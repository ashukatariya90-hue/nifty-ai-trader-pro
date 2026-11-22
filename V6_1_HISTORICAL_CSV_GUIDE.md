# V6.1 Historical CSV Guide

Use an authorized historical dataset that you are permitted to use. The app does not verify exchange origin, licensing or completeness.

## Required header

`Date,Open,High,Low,Close,Volume`

## Supported date values

- Daily bars may use `YYYY-MM-DD`. These are normalized to UTC midnight for ordering only; no intraday time is inferred.
- Timestamped bars must be ISO-8601 with a timezone, for example `2026-01-01T09:15:00+05:30` or `2026-01-01T03:45:00Z`.
- Timezone-naive timestamp values are rejected.

## Data requirements

- At least 50 rows and no more than 20,000 rows.
- Maximum CSV size: 2 MB.
- Rows must be in strictly increasing date/time order with no duplicates.
- OHLC prices must be finite and positive; candle geometry must be valid.
- Volume must be finite and non-negative.
- Missing rows are not filled or fabricated.

## Run research in the app

1. Open **Analysis** and import the CSV.
2. Open **Momentum**.
3. Find **Imported Historical CSV Research**.
4. Tap **Analyse Imported Historical CSV**.
5. Review data validity, factor context and walk-forward results.

The dataset structure check does not prove authenticity. If no bar interval is supplied, interval-gap detection is explicitly not run. Walk-forward output is a descriptive EMA baseline, not a trading strategy or accuracy guarantee. No trade instructions or real orders are generated.
