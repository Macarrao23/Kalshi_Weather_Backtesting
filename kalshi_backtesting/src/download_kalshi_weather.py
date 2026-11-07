"""Export public Kalshi high-temperature market metadata and settlement outcomes.

Run:
    python src/download_kalshi_weather.py --start 2026-01-01 --end 2026-09-22

Requires requests. Read-only; no API credentials or trading calls.
This is a market/outcome export, not a historical executable-price dataset.
"""

import argparse
import csv
import time
from datetime import datetime, date
from pathlib import Path

import requests

BASE = "https://external-api.kalshi.com/trade-api/v2"
SERIES = {
    "Miami": "KXHIGHMIA",
    "Phoenix": "KXHIGHTPHX",
    "Atlanta": "KXHIGHTATL",
    "Seattle": "KXHIGHTSEA",
}

COLUMNS = [
    "city", "series_ticker", "event_date", "event_ticker", "ticker",
    "status", "result", "floor_strike", "cap_strike",
    "open_time", "close_time", "settlement_ts", "rules_primary",
]


def fetch_paginated(session, endpoint, params):
    cursor = None
    while True:
        query = dict(params)
        if cursor:
            query["cursor"] = cursor
        for attempt in range(7):
            resp = session.get(BASE + endpoint, params=query, timeout=45)
            if resp.status_code in (429, 500, 502, 503, 504):
                time.sleep(min(2 ** attempt, 30))
                continue
            resp.raise_for_status()
            break
        else:
            raise RuntimeError(f"Repeated errors from {endpoint}")

        body = resp.json()
        yield from body.get("markets", [])
        cursor = body.get("cursor")
        if not cursor:
            break
        time.sleep(0.1)


def event_day(event_ticker):
    # Weather event tickers typically have CITY-YYMONDD format.
    parts = (event_ticker or "").split("-")
    if len(parts) < 2:
        return None
    try:
        return datetime.strptime(parts[1].upper(), "%y%b%d").date()
    except ValueError:
        return None


def collect(start: date, end: date, output: Path):
    if start > end:
        raise ValueError("Start date is after end date")
    output.parent.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    session.headers.update({"User-Agent": "kalshi-weather-research-export/1.0"})
    rows = {}

    for city, series in SERIES.items():
        print(f"Collecting {city} ({series})...")
        for endpoint, params in [
            ("/historical/markets", {"series_ticker": series, "limit": 1000}),
            ("/markets", {"series_ticker": series, "status": "settled", "limit": 1000,
                          "mve_filter": "exclude"}),
        ]:
            for market in fetch_paginated(session, endpoint, params):
                if market.get("status") != "settled":
                    continue
                date_value = event_day(market.get("event_ticker", ""))
                if date_value is None or not start <= date_value <= end:
                    continue
                ticker = market.get("ticker")
                if not ticker:
                    continue
                row = {"city": city, "series_ticker": series,
                       "event_date": date_value.isoformat()}
                row.update({k: market.get(k, "") for k in COLUMNS if k not in row})
                rows[ticker] = row

    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(sorted(rows.values(), key=lambda r: (r["event_date"], r["city"], r["ticker"])))
    print(f"Saved {len(rows)} settled market rows to {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", default="2026-01-01", help="YYYY-MM-DD")
    parser.add_argument("--end", default="2026-09-22", help="YYYY-MM-DD")
    parser.add_argument("--output", default="data/kalshi_weather_markets.csv")
    args = parser.parse_args()
    collect(date.fromisoformat(args.start), date.fromisoformat(args.end), Path(args.output))
