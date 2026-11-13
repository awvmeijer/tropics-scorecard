# Tropics Scorecard

How close was the forecast to what the instruments measured, and how sure are we?

This repository scores hourly rain, temperature and wind forecasts for Singapore against station observations, not against a reanalysis. Every comparison carries a 95 percent interval.

[![Summary page](https://img.shields.io/badge/summary-live%20page-1e9bff?style=flat-square)](https://awvmeijer.github.io/tropics-scorecard/)
[![Tests](https://img.shields.io/badge/tests-100%20passing-1e9bff?style=flat-square)](tests)
[![Findings](https://img.shields.io/badge/findings-9-262626?style=flat-square)](docs/findings.md)

**[Read the one-page summary](https://awvmeijer.github.io/tropics-scorecard/)**: a scorecard across lead days, an extremes test, a decision score, the reanalysis as a second judge, three replayed events, and what the checks caught.

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/assets/pipeline-dark.svg">
    <source media="(prefers-color-scheme: light)" srcset="docs/assets/pipeline-light.svg">
    <img alt="Tropics Scorecard pipeline: station observations and archived forecasts are matched on the same cases, scored against two baselines through one scorer, and reported with intervals." src="docs/assets/pipeline-light.svg" width="100%">
  </picture>
</p>

## What it found

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/assets/result-dark.svg">
    <source media="(prefers-color-scheme: light)" srcset="docs/assets/result-light.svg">
    <img alt="Difference in mean absolute error against climatology, one day ahead, with 95 percent intervals. Rain forecasts are slightly better than climatology; temperature and wind forecasts are worse." src="docs/assets/result-light.svg" width="100%">
  </picture>
</p>

- **At the surface in the tropics, operational forecasts barely beat a free guess.** No model is detectably better than climatology for temperature or wind at a station, at any lead time. For rain, ECMWF gains about 12 percent.
- **The events that matter most are where they miss.** ECMWF's heaviest 6-hour rain totals are a third of what the gauges measured, even with the gauges averaged over the model's own grid cell. Acting on the best forecast for heavy rain keeps about 13 percent of what a perfect one would save. A squall line put 10 mm in an hour on half of Singapore's gauges, and no forecast had it at any lead time.
- **The judge needs as much care as the model.** Judged by the ERA5 reanalysis instead of the instruments, the order of GFS and ECMWF flips for temperature, and ERA5 itself is further from the thermometers than a free climatology. One matching choice moves a score as much as switching models, and two of the first "wins" were faults in the forecast archive.

If a weather model is meant to learn from observations, it should be judged on them too. This repository is a small, working version of that judge.

The full write-up is in [docs/findings.md](docs/findings.md), the case studies in [docs/cases/](docs/cases/), and what went wrong and why in [docs/failure_modes.md](docs/failure_modes.md).

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
| Summary tables | A scorecard of the change in error against climatology at every lead day, and an extremes test comparing the heaviest 6-hour rain totals with the gauges, alone and averaged over each grid cell |
| Decision value | How much of a perfect forecast's saving a user keeps by protecting whenever the forecast says 10 mm of rain or more, for every ratio of the cost of protecting to the loss avoided |
| Reanalysis | ERA5, scored against the stations like a forecast, and used as a second judge of the same forecasts on the same station-hours |

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
uv run python -m tropics_scorecard.ingest.era5 all
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
- Reanalysis: ERA5, Copernicus Climate Change Service, via [Open-Meteo.com](https://open-meteo.com/), CC BY 4.0. One grid cell per station, unchanged.
- Coastline: Natural Earth, public domain.
