# Tropics Scorecard

How close was the forecast to what the instruments measured, and how sure are we?

This repository scores hourly rain, temperature and wind forecasts for Singapore and the area around it against station observations, not against a reanalysis. Every comparison carries a 95 percent interval.

Status: first full results, November 2026. Findings are in [docs/findings.md](docs/findings.md), case studies in [docs/cases/](docs/cases/), and what went wrong and why in [docs/failure_modes.md](docs/failure_modes.md).

## Limits, first

- A rain gauge measures one point. A forecast is an average over a grid cell 9 to 28 km wide, so it shows more light rain and less heavy rain than any gauge. Part of every low rain score comes from that mismatch.
- Stations have errors. Tipping-bucket gauges catch less rain than falls in strong wind and very heavy rain. No correction is applied.
- The test period is under three years (February 2024 to October 2026), so each monsoon phase appears two or three times.
- Two of the models publish rain in 3-hour or 6-hour steps, so hourly rain is not a fair test for them. Rain is also scored as 6-hour totals.
- This is one region and one set of public archives. It is not a benchmark of record.

## What is scored

| | |
|---|---|
| Observations | Singapore station network (data.gov.sg): about 50 to 70 rain gauges at 5 minutes, depending on the year, and 13 weather stations at 1 minute. Airport reports (NOAA ISD) for temperature and wind. Changi soundings (IGRA) for case studies |
| Forecasts | GFS and ECMWF IFS 0.25° at lead days 1, 2, 3, 5 and 7 (Open-Meteo Previous Runs); whole runs from April 2026 for hour-by-hour lead times. ECMWF AIFS and IFS 9 km on their shorter archives, scored apart |
| Baselines | Persistence and climatology, exposed exactly like a model |
| Intervals | Moving-block bootstrap over days, on paired differences between two forecasts on the same cases |

The rules are written down before any scoring in [docs/verification_protocol.md](docs/verification_protocol.md), with a dated change log. How each observation source fails, and which check catches it, is in [docs/observation_notes/](docs/observation_notes/).

## Run it

```
uv sync
uv run python -m tropics_scorecard.pipeline all
```

The second command rebuilds every table from the downloaded data, scores every forecast and writes the dashboard data. Downloading is separate, because the full archive takes hours:

```
uv run python -m tropics_scorecard.ingest.datagovsg rainfall 2024-02-04 2026-10-31 --v1
uv run python -m tropics_scorecard.ingest.openmeteo all
```

The dashboard is a static site in `dashboard/`. Serve it with any static server, for example `python -m http.server -d dashboard`.

## Layout

```
ingest/     one module per source; raw responses cached under data/raw/
store/      tidy Parquet tables, read through DuckDB
qc/         range, spike, flatline, duplicate, stuck-gauge and clock checks; every flag logged
match/      the hourly reference the forecasts are scored against
sources/    one interface for anything that forecasts; operational models
baselines/  persistence and climatology
scorer/     scores, comparisons and intervals; all maths in metrics/
metrics/    the metric functions, standard library only
cases/      replay one event from one command
dashboard/  static site reading precomputed JSON
```

## Data and attribution

- Singapore weather station data: Meteorological Service Singapore, via [data.gov.sg](https://data.gov.sg), Singapore Open Data Licence.
- Airport observations: NOAA National Centers for Environmental Information, Integrated Surface Database.
- Soundings: NOAA Integrated Global Radiosonde Archive, version 2.
- Forecasts: [Weather data by Open-Meteo.com](https://open-meteo.com/), CC BY 4.0. Values are taken from one grid cell per station, unchanged.
- Coastline: Natural Earth, public domain.
