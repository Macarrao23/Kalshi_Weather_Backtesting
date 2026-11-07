# Kalshi Weather Market Backtesting & Analytics

**Python + Excel | Prediction-market data research | Historical simulations**

An independent research project evaluating Kalshi daily-high temperature markets in **Miami, Phoenix, Atlanta, and Seattle**. It combines public Kalshi market and historical trade data, settlement outcomes, and archived **Open-Meteo previous-day forecasts** to test rules for buying **NO** contracts in the lowest temperature bucket. Results are visualized in an Excel dashboard.

This repository is **read-only research**: no order placement, API trading keys, or live automated execution.

## Research snapshot (Jan 1–Sep 22, 2026)

| City | Simulated trades | Wins | Losses | Observed win rate | Gross simulated P&L |
| --- | ---: | ---: | ---: | ---: | ---: |
| Miami | 146 | 141 | 5 | 96.58% | $17.95 |
| Phoenix | 105 | 97 | 8 | 92.38% | $20.71 |
| Atlanta | 124 | 112 | 12 | 90.32% | $18.72 |
| Seattle | 67 | 42 | 25 | 62.69% | $17.70 |
| **Total** | **442** | **392** | **50** | **88.69%** | **$75.08** |

These are **retrospective simulated outcomes, not account profits**. The $75.08 figure is **gross, before fees, bid/ask spread, slippage, and execution limitations**. Historical trades are not guaranteed executable entry quotes. The project does **not** demonstrate a verified live trading edge. The date range is **not a full year**; September is partial, and city coverage varies.

## Strategy and analysis

- Pull settled daily-high temperature markets and their YES/NO outcomes from Kalshi's **public REST API**.
- For each event, identify its lowest-temperature contract and examine a threshold-based NO entry: **Miami ≤95¢, Phoenix ≤85¢, Atlanta ≤85¢, Seattle ≤45¢**.
- Reconstruct historical first-qualifying public trade prints and mark wins/losses from settlement outcomes. The original summary uses **two simulated NO contracts per qualifying event** and no more than one selected trade per event.
- Use prior-day forecasts from **Open-Meteo's Previous Runs API** in a separate forecast-filter experiment. This is **not** historical MSN forecast data.
- Analyze win rate, per-city performance, gross P&L, and bucket frequencies. A separate Miami study counted **364 valid settled events**; it is not part of the 442 simulated trade count.

## Files

```text
Kalshi_Weather_GitHub_Ready/
├── README.md
├── requirements.txt
├── .gitignore
├── src/
│   ├── download_kalshi_weather.py
│   └── backtest_4cities_forecast_filter_FIXED_FULL.py
├── results/
│   ├── Kalshi_Weather_Backtesting_Portfolio_Dashboard.xlsx
│   └── Kalshi_Weather_4City_YTD_Backtest_2026.xlsx
└── data/                       # created by the download script
```

- `results/Kalshi_Weather_Backtesting_Portfolio_Dashboard.xlsx`: polished research dashboard and methods/limitations notes.
- `results/Kalshi_Weather_4City_YTD_Backtest_2026.xlsx`: the original four-city summary and monthly results.
- `src/download_kalshi_weather.py`: **new standalone helper** that exports Kalshi settled contract metadata and outcomes to CSV.
- `src/backtest_4cities_forecast_filter_FIXED_FULL.py`: existing four-city historical-trade and Open-Meteo forecast-filter analysis code. It prints results and can require many public API calls.

**Important reproducibility distinction:** The supplied Excel summaries do not contain all underlying trade-level observations or a frozen public-data snapshot. The backtesting script is a research variant; its current output is **not guaranteed to reproduce the dashboard's exact 442-trade sample**. Reproducing a historical backtest precisely requires versioned input snapshots, matching cutoff dates and data filters, and a fee/execution model.

## Run locally (Windows PowerShell)

1. Download this repository: **Code → Download ZIP** on GitHub, then unzip it, or clone with Git.
2. Open PowerShell in the repository folder.
3. Set up Python:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

4. Download historical **settled market metadata and outcomes** to a CSV:

```powershell
python src/download_kalshi_weather.py --start 2026-01-01 --end 2026-09-22
```

Output: `data/kalshi_weather_markets.csv`. This has one row per settled contract, not one row per event. It **does not include historical price prints or forecasts**.

5. Run the research variant that pulls trades and Open-Meteo previous-run forecasts:

```powershell
python src/backtest_4cities_forecast_filter_FIXED_FULL.py
```

This script uses its own date constants and prints per-city and combined results. It is a separate forecast-filter experiment, rather than a direct exporter for every Excel row. Kalshi's historical API may return changed or corrected metadata; endpoint/data availability and rate limits can also affect repeat runs.

On Mac/Linux, use `python3` and `source .venv/bin/activate` instead of the Windows virtual-environment commands.

## Data sources and API notes

- [Kalshi API historical-data guide](https://docs.kalshi.com/getting_started/historical_data)
- [Kalshi historical markets endpoint](https://docs.kalshi.com/api-reference/historical/get-historical-markets)
- [Open-Meteo Previous Runs API](https://open-meteo.com/en/docs/previous-runs-api)

Kalshi splits public data between live/recent and historical routes. The **historical cutoff moves over time**. The scripts request both archived `/historical/markets` and recent `/markets`; the backtest research script also pulls `/historical/trades` and `/markets/trades`. The API is public for these market-data GET calls, with **no trading credentials required**.

The README should not be interpreted as a guarantee of any market's settlement weather source. For precise evaluation, verify each contract's terms and designated settlement observation separately; a forecast for a nearby airport is not necessarily the official settlement series.

## Limitations and integrity

- Historical trade prints may not equal a fillable NO ask for two contracts.
- Gross P&L excludes exchange fees, spread, slippage, and market impact.
- Higher win rates do not necessarily imply profitable expected returns.
- Forecast filters use a smaller sample and are descriptive, not proof of causality.
- Archived forecasts should be matched by issue time to prevent look-ahead bias.
- Publishing code and summary spreadsheets alone is **partial reproducibility**; also publish frozen input records and validated test outputs if you want exact third-party auditability.

*Independent educational research. Not affiliated with Kalshi. Not financial advice.*
