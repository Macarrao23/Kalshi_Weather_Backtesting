import requests
import time
from collections import defaultdict
from datetime import datetime, timezone

KALSHI = "https://api.elections.kalshi.com/trade-api/v2"
OPEN_METEO = "https://previous-runs-api.open-meteo.com/v1/forecast"

START_DATE = "2026-01-01"
END_DATE = "2026-09-22"
START_TS = int(datetime(2026, 1, 1, tzinfo=timezone.utc).timestamp())
END_TS = int(datetime(2026, 9, 23, tzinfo=timezone.utc).timestamp())

CITIES = {
    "Miami": ("KXHIGHMIA", 95, 25.7959, -80.2870, "America/New_York"),
    "Phoenix": ("KXHIGHTPHX", 85, 33.4342, -112.0116, "America/Phoenix"),
    "Atlanta": ("KXHIGHTATL", 85, 33.6407, -84.4277, "America/New_York"),
    "Seattle": ("KXHIGHTSEA", 45, 47.4502, -122.3088, "America/Los_Angeles"),
}

SESSION = requests.Session()


def get_json(url, params=None, retries=10):
    wait = 1

    for _ in range(retries):
        response = SESSION.get(url, params=params, timeout=60)

        if response.status_code == 429:
            print(f"Rate limited. Waiting {wait}s...")
            time.sleep(wait)
            wait = min(wait * 2, 30)
            continue

        if not response.ok:
            print("FAILED:", response.status_code, response.url)
            print(response.text[:1000])
            response.raise_for_status()

        return response.json()

    raise RuntimeError("Too many rate limits.")


def get_markets(series, historical):
    path = "/historical/markets" if historical else "/markets"
    output = []
    cursor = None

    while True:
        params = {"series_ticker": series, "limit": 1000}

        if not historical:
            params["status"] = "settled"
            params["mve_filter"] = "exclude"

        if cursor:
            params["cursor"] = cursor

        data = get_json(KALSHI + path, params)
        output.extend(data.get("markets", []))

        cursor = data.get("cursor")
        if not cursor:
            return output


def market_timestamp(market):
    for key in ("settlement_ts", "close_time", "expiration_time"):
        value = market.get(key)

        if not value:
            continue

        try:
            return int(
                datetime.fromisoformat(
                    value.replace("Z", "+00:00")
                ).timestamp()
            )
        except Exception:
            continue

    return None


def to_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def event_ticker(market):
    value = market.get("event_ticker")
    if value:
        return value

    ticker = market.get("ticker", "")
    parts = ticker.split("-")
    return "-".join(parts[:2]) if len(parts) >= 2 else ticker


def event_date(event):
    try:
        code = event.split("-")[1]
        return datetime.strptime(code, "%y%b%d").date().isoformat()
    except Exception:
        return None


def lowest_bucket(markets):
    candidates = []

    for market in markets:
        floor = to_float(market.get("floor_strike"))
        cap = to_float(market.get("cap_strike"))

        if floor is None and cap is not None:
            candidates.append(market)

    if not candidates:
        return None

    return min(
        candidates,
        key=lambda market: to_float(market.get("cap_strike"))
    )


def get_trades(ticker, historical):
    path = "/historical/trades" if historical else "/markets/trades"
    output = []
    cursor = None

    while True:
        params = {
            "ticker": ticker,
            "limit": 1000,
            "min_ts": START_TS,
            "max_ts": END_TS,
        }

        if cursor:
            params["cursor"] = cursor

        data = get_json(KALSHI + path, params)
        output.extend(data.get("trades", []))

        cursor = data.get("cursor")
        if not cursor:
            return output


def no_price_cents(trade):
    value = trade.get("no_price_dollars")
    if value is not None:
        return float(value) * 100

    value = trade.get("no_price")
    if value is not None:
        value = float(value)
        return value * 100 if value <= 1 else value

    value = trade.get("yes_price_dollars")
    if value is not None:
        return 100 - float(value) * 100

    value = trade.get("yes_price")
    if value is not None:
        value = float(value)
        value = value * 100 if value <= 1 else value
        return 100 - value

    return None


def first_qualifying_trade(trades, limit):
    qualifying = []

    for trade in trades:
        price = no_price_cents(trade)

        if price is None:
            continue

        if price <= limit:
            qualifying.append(
                (trade.get("created_time", ""), price)
            )

    if not qualifying:
        return None

    return min(qualifying, key=lambda item: item[0])


def get_forecast_highs(lat, lon, timezone_name):
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "temperature_2m_previous_day1",
        "temperature_unit": "fahrenheit",
        "timezone": timezone_name,
        "start_date": START_DATE,
        "end_date": END_DATE,
    }

    data = get_json(OPEN_METEO, params)
    hourly = data.get("hourly", {})

    times = hourly.get("time", [])
    temperatures = hourly.get("temperature_2m_previous_day1", [])

    daily = defaultdict(list)

    for stamp, temperature in zip(times, temperatures):
        if temperature is not None:
            daily[stamp[:10]].append(float(temperature))

    return {
        day: max(values)
        for day, values in daily.items()
        if values
    }


def print_result(label, rows):
    trade_count = len(rows)
    wins = sum(1 for row in rows if row["win"])
    losses = trade_count - wins
    pnl = sum(row["pnl"] for row in rows)

    win_rate = (
        wins / trade_count * 100
        if trade_count
        else 0
    )

    print(
        f"{label:<18}"
        f" Trades {trade_count:>4}"
        f" | Wins {wins:>4}"
        f" | Losses {losses:>3}"
        f" | Win Rate {win_rate:>6.2f}%"
        f" | Gross P&L ${pnl:>7.2f}"
    )


def main():
    cutoff_data = get_json(KALSHI + "/historical/cutoff")
    cutoff_text = cutoff_data["market_settled_ts"]

    cutoff_ts = int(
        datetime.fromisoformat(
            cutoff_text.replace("Z", "+00:00")
        ).timestamp()
    )

    print("=" * 100)
    print("4-CITY YTD 2026 FORECAST FILTER BACKTEST")
    print("=" * 100)
    print("Forecast source: Open-Meteo archived previous-day forecast")
    print("This is NOT an MSN historical forecast backtest.")
    print("Testing margins: 0F, +1F, +2F, +3F")
    print()

    all_rows = []

    for city, config in CITIES.items():
        series, price_limit, lat, lon, timezone_name = config

        print(f"{city}: downloading archived forecasts...")

        forecasts = get_forecast_highs(
            lat,
            lon,
            timezone_name,
        )

        historical_markets = get_markets(series, True)
        recent_markets = get_markets(series, False)

        merged = {}

        for market in historical_markets + recent_markets:
            ticker = market.get("ticker")
            if ticker:
                merged[ticker] = market

        events = defaultdict(list)

        for market in merged.values():
            timestamp = market_timestamp(market)

            if timestamp is None:
                continue

            if START_TS <= timestamp < END_TS:
                events[event_ticker(market)].append(market)

        rows = []

        print(
            f"  YTD events: {len(events)}"
            f" | forecast days: {len(forecasts)}"
        )

        for event, event_markets in sorted(events.items()):
            market = lowest_bucket(event_markets)

            if market is None:
                continue

            day = event_date(event)

            if day is None or day not in forecasts:
                continue

            bucket_ceiling = to_float(
                market.get("cap_strike")
            )

            if bucket_ceiling is None:
                continue

            timestamp = market_timestamp(market)

            is_historical = (
                timestamp is not None
                and timestamp < cutoff_ts
            )

            trade_data = get_trades(
                market["ticker"],
                is_historical,
            )

            entry = first_qualifying_trade(
                trade_data,
                price_limit,
            )

            if entry is None:
                continue

            forecast_high = forecasts[day]
            distance = forecast_high - bucket_ceiling

            win = (
                str(market.get("result", ""))
                .lower()
                .strip()
                == "no"
            )

            entry_price = entry[1] / 100.0
            pnl = (1.0 - entry_price) if win else -entry_price

            rows.append({
                "city": city,
                "day": day,
                "forecast": forecast_high,
                "bucket_ceiling": bucket_ceiling,
                "distance": distance,
                "win": win,
                "pnl": pnl,
            })

        all_rows.extend(rows)

        print_result("PRICE ONLY", rows)

        for margin in (0, 1, 2, 3):
            filtered = [
                row
                for row in rows
                if row["distance"] >= margin
            ]

            print_result(
                f"FORECAST +{margin}F",
                filtered,
            )

        print()

    print("=" * 100)
    print("COMBINED")
    print("=" * 100)

    print_result("PRICE ONLY", all_rows)

    for margin in (0, 1, 2, 3):
        filtered = [
            row
            for row in all_rows
            if row["distance"] >= margin
        ]

        print_result(
            f"FORECAST +{margin}F",
            filtered,
        )

    print()
    print("MONTHLY RESULTS - +1F RULE")
    print("-" * 100)

    plus_one = [
        row
        for row in all_rows
        if row["distance"] >= 1
    ]

    months = sorted(
        set(row["day"][:7] for row in plus_one)
    )

    for month in months:
        month_rows = [
            row
            for row in plus_one
            if row["day"].startswith(month)
        ]

        print_result(
            month,
            month_rows,
        )

    print()
    print("Fees/slippage excluded.")
    print("Forecast source: Open-Meteo Previous Runs API, not MSN.")


if __name__ == "__main__":
    main()
