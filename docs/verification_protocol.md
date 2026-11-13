# Verification protocol

Written before any scoring. Changed only with a dated note at the bottom saying what changed and why.

**Status: decisions 1 to 9 accepted by the author on 13 November 2026, before any forecast was scored.** Lines marked ACCEPTED were proposals in the draft of 11 November. Still open: sections 1 and 8 (the author's own words), and the bootstrap block length, which is fixed from baseline errors before any model is scored (section 7).

## 1. The decisions these scores should inform

Who would use this forecast, and for what? Write two or three concrete decisions. Each metric below must trace back to one of them.

Suggestions to replace or keep, not decisions:

- Whether to schedule outdoor work or events for an afternoon one to three days ahead. Needs: rain occurrence by hour of day, at day-level lead times.
- Whether a heavy-rain hour (10 mm or more) is likely tomorrow, for drainage or flood readiness. Needs: hits and false alarms above 10 mm in an hour.
- Whether a forecast is worth using at all at a given lead time, against free baselines. Needs: the lead time at which each forecast stops beating persistence and climatology.

## 2. Reference

The reference is the station observation after quality control. Not a reanalysis.

- **Observation error.** ACCEPTED: no correction for gauge undercatch or sensor error. Flagged readings are removed from the main table, and every table is computed a second time with flagged readings kept, so the effect of quality control is visible. The size of known errors (tipping-bucket undercatch in heavy rain and wind) is stated in the limits, not modelled.
- **Point against grid cell.** A gauge measures one point; the forecast is an average over a cell 9 to 28 km wide. For rain this means a forecast will show more light rain and less heavy rain than any gauge, and hit scores at high thresholds are pulled down by the mismatch, not only by forecast error. For temperature and wind it means a coastal or urban station can differ from its cell for reasons the model cannot represent. ACCEPTED: every results page carries this sentence, and the frequency of each rain category is shown next to its scores, so a reader can see how much of a low score comes from the mismatch.

## 3. Matching

### 3.1 Grid point

Each forecast is the raw value of one model grid cell, requested from Open-Meteo with `cell_selection=nearest` and `elevation=nan`, so no land preference and no elevation correction is applied by the provider. Which cell a station is paired with is the choice here.

Evidence (`data/tables/openmeteo/grid.parquet`, 76 stations):

| Model | Grid | Stations whose cell differs between the two rules | Cells used, nearest / land |
|---|---|---|---|
| ECMWF IFS 0.25 | 0.25 degrees | 53 of 76 | 9 / 8 |
| ECMWF AIFS 0.25 | 0.25 degrees | 53 of 76 | 9 / 8 |
| ECMWF IFS 9 km | about 9 km | 13 of 76 | 24 / 19 |
| GFS | about 0.12 degrees (13 km) | 7 of 76 | 13 / 11 |

For the ECMWF 0.25 degree grids, the two rules differ because of how such a grid sees Singapore. The cell that contains most of the island (centred at 1.25 N, 103.75 E, spanning 1.125 to 1.375 N) is mostly sea in the model, with a mean height of 0 m. Under the nearest rule a station is paired with the cell it sits in. Under the land rule Open-Meteo skips that cell and pairs 53 of the 54 Singapore stations south of 1.375 N with a cell centred in Johor, at 1.5 N, which does not contain them. The finer grids are affected less: for GFS the two rules differ for 7 stations. The station map on the dashboard shows both.

- ACCEPTED: pair each station with the nearest cell, which is the cell the station sits in. It is what the model said about that place. If the model's cell is too marine to hold Singapore's daily temperature cycle, that is a real limit of a 28 km grid and belongs in the results, not moved out of them by pairing with a cell in another country. The land rule is scored as a sensitivity check on the same cases and reported in one table, so the reader can see how much the choice matters.
- This proposal was changed on 11 November, before any forecast was scored, after the cells were mapped (see the change log).
- ACCEPTED: no interpolation between cells. Interpolation smooths the model's own values and makes rain lighter and more widespread.

### 3.2 Time

- Forecast rain from Open-Meteo is the total over the hour ending at its time stamp (the first hour of a run is empty, checked 2026-11-10). Temperature and wind are instantaneous values at the time stamp.
- Gauge readings are five-minute totals. The provider does not say whether a stamp marks the start or the end of its five minutes. In January to April 2017 stamps fell one second before each five-minute mark (for example 23:59:59), which points to the end. ACCEPTED: a stamp marks the end of its interval, so readings stamped 10:05 to 11:00 make the hour ending 11:00. This is tested before scoring by comparing gauge hourly totals at Changi with the airport record both ways; if the test points the other way, this line changes with a dated note.
- All matching is in UTC. Hour of day is reported in Singapore time (UTC plus 8 hours, no daylight saving).

### 3.3 Instantaneous variables

- Temperature (`DBT 1M F`) is a one-minute reading. Wind speed (`AVG(S)10M M1M`) appears from its reading type to be a 10-minute average reported every minute. To confirm in the station note.
- ACCEPTED: pair the forecast with the reading stamped exactly on the hour. If that reading is missing or flagged, the hour is dropped, not filled from a neighbouring minute. Alternative: the mean of the readings from 5 minutes before to 5 minutes after the hour. It is less noisy but no longer the same moment as the forecast.
- Airport reports (ISD): ACCEPTED: the report stamped on the hour, taking the SYNOP (temperature in tenths of a degree) over the METAR (whole degrees) when both exist. Half-hour reports are not used.
- Units: station wind in knots is converted to metres per second (times 0.514444). Forecasts are requested in metres per second.

### 3.4 Missing values

Evidence: from 11 February 2024 to 31 December 2025, 99.17 percent of station-hours with any rain reading have all 12 five-minute readings; 0.27 percent have 11.

- ACCEPTED: a rain hour is kept only when all 12 readings are present and none is flagged. Partial hours cannot be told apart from dry minutes, so filling them would bias totals low.
- Temperature and wind: see 3.3.

### 3.5 Lead time

- Previous Runs, lead day N: the value from the run that was current N times 24 hours before the valid time. The true lead is therefore between 24N hours and 24N hours plus the gap between runs. Results say "day N", not a number of hours.
- Single Runs (from 2 April 2026): the lead is the valid time minus the run time, in whole hours. ACCEPTED: runs at 00 and 12 UTC only.

## 4. Variables, thresholds and metrics

Evidence: from 11 February 2024 to 31 December 2025 (975,505 complete station-hours), an hour reached 0.1 mm in 8.27 percent of cases, 1 mm in 4.30 percent, 10 mm in 0.91 percent (8,910 station-hours), 20 mm in 0.32 percent and 30 mm in 0.13 percent. 19 of 63 gauges tip at slightly under 0.2 mm, so a 0.2 mm threshold would miss a single tip on those gauges.

| Variable | Question | Metric | Threshold | Why this one |
|---|---|---|---|---|
| Hourly rain occurrence | Did it rain at the gauge in this hour? | Probability of detection, false alarm ratio, critical success index, equitable threat score; Brier score with the forecast as 0 or 1 | ACCEPTED: 0.1 mm (one tip on any gauge) | The most common decision: rain or no rain |
| Heavier rain | Was it a wet hour, or a downpour? | Same categorical scores | ACCEPTED: 1 mm and 10 mm | 10 mm is rare (under 1 percent of hours) but still gives thousands of cases; 30 mm gives too few for stable intervals |
| Hourly rain amount | How much fell? | Mean error (bias), mean absolute error (MAE), root mean square error (RMSE) | none | MAE is the headline; RMSE is dominated by a few downpours and is shown second |
| Temperature at 2 m | How warm was it? | Bias, MAE, RMSE | none | The easy case and a check that the pipeline is right |
| Wind speed at 10 m | How windy was it? | Bias, MAE, RMSE | none | Shows the point against grid cell problem clearly |

The categorical scores are computed from one contingency table per group (forecast source, lead time, hour, phase), not averaged over stations.

## 5. Baselines

Both baselines are exposed exactly like a model and scored on the same cases.

### 5.1 Persistence

- ACCEPTED, lead day N: the observation at the same station 24N hours before the valid time. This is what an observer would have known when the day-N forecast was issued, and it keeps the daily cycle, which matters in the tropics.
- ACCEPTED, Single Runs: two persistence forecasts, labelled apart. Persistence at issue: the observation at the run time, for every lead. Daily persistence: the observation 24 hours before the valid time.
- For rain occurrence, persistence says yes when the observed hour reached the threshold.

### 5.2 Climatology

- ACCEPTED: per station, calendar month and local hour, from 2017-01-01 to 2023-12-31 (station data from the same network, no overlap with the test period, which starts 2024-02-11).
- Continuous variables: the mean. Rain occurrence: the observed frequency, used as a probability for the Brier score and as "yes" when it is 0.5 or more for the categorical scores.
- ACCEPTED: a station with fewer than three years of history in 2017 to 2023 uses the mean of all stations for that month and hour, and is marked in the results.

## 6. Stratification

### 6.1 Lead time

ACCEPTED: days 1, 2, 3, 5 and 7 (Previous Runs). For Single Runs, every hour from 1 to 168 for curves, and six-hour bins for tables.

### 6.2 Hour of day

Local time, each hour. Afternoon convection is the expected weak spot. Report what is found, not what is expected.

### 6.3 Monsoon phase

The Meteorological Service Singapore describes four periods: Northeast Monsoon December to early March, inter-monsoon late March to May, Southwest Monsoon June to September, inter-monsoon October to November ([Climate of Singapore](https://www.weather.gov.sg/climate-climate-of-singapore/)).

ACCEPTED: fixed calendar dates for every year, with the March boundary on the 15th: Northeast Monsoon 1 December to 15 March, first inter-monsoon 16 March to 31 May, Southwest Monsoon 1 June to 30 September, second inter-monsoon 1 October to 30 November. Fixed dates are chosen before seeing any score. Each year's announced onset dates would fit the seasons better but would be a choice made per year.

## 7. Uncertainty

- **Paired differences.** Every comparison is a forecast against a baseline, or one forecast against another, on exactly the same cases (station, valid time, lead time). Cases missing from either side are dropped from both.
- **The paired quantity.** ACCEPTED: absolute error for continuous variables (so the interval is on the difference in MAE), and the per-case Brier score for rain occurrence. Equitable threat score and the other contingency scores have no per-case value, so they are shown with their sample size but without an interval, and no comparison is drawn from them alone.
- **Time correlation.** ACCEPTED: for each day, average the paired quantity over the stations and hours in the group, then run a moving-block bootstrap on that daily series in time order (`metrics.bootstrap.block_bootstrap_ci_mean_diff`). Averaging over stations first keeps their shared weather in one value, so the intervals are not narrowed by stations that move together. Days rather than hours keep the series short enough to resample 2000 times for every group.
- **Block length.** ACCEPTED: fixed before any model is scored, from the autocorrelation of the daily persistence-minus-climatology series for each variable: the first lag in days below 0.1, at least 2 days.
- **Intervals on single scores.** The same bootstrap, run on one source's daily series against zero, gives the interval shown next to a single MAE, bias or Brier score. RMSE gets its interval from the interval on the mean squared error, square-rooted.
- **Resamples and level.** 2000 resamples, 95 percent percentile intervals, seed 0 (in `config/study.yaml`).
- **No detectable difference.** The interval contains zero. That result is reported as it is, not as a tie or a win.

## 8. What this protocol cannot tell you

Write the limits here before seeing results. Prompts to answer in your own words:

- What does a gauge-to-cell comparison say about a forecast for an area, and what does it not?
- How long is the test period in years, and how many of each monsoon phase does it hold?
- Which forecasts are scored on a shorter period, and why their numbers are not pooled with the main table.
- What the archive does and does not let us say about lead times shorter than one day before April 2026.

## Change log

| Date | Change | Reason |
|---|---|---|
| 2026-11-11 | First draft with proposals | Written before any forecast was scored |
| 2026-11-11 | Proposal 3.1 changed from the land rule to the nearest cell | Mapping the cells showed the land rule pairs stations south of 1.375 N with cells in Johor that do not contain them. No forecast had been scored |
| 2026-11-13 | Decisions 1 to 9 accepted as drafted | Sign-off by the author; no forecast had been scored |
| 2026-11-13 | Bootstrap block length fixed at 8 days | First lag below 0.1 in the autocorrelation of daily persistence-minus-climatology MAE at lead day 1: rain 3 days, temperature 7, wind 8. The largest is used for all variables. No model forecast was read (`scripts/fix_block_length.py`) |
