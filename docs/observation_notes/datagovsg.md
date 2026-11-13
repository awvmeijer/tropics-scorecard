# Observation note: Singapore station network (data.gov.sg, collection 1459)

Rain facts in the failure table come from a sample week (4 to 10 February 2024, 63 gauges, 124,768 readings) unless marked; counts for the whole period come from the quality-control log. Humidity and wind direction are not downloaded.

## What it measures

| Variable | Reading type in the response | Unit | Step |
|---|---|---|---|
| Rain | TB1 Rainfall 5 Minute Total F | mm | 5-minute total from a tipping-bucket gauge |
| Air temperature | DBT 1M F | deg C | 1 minute |
| Relative humidity | RH 1M F | percent | 1 minute |
| Wind speed | Wind Speed AVG(S)10M M1M | knots | 1 minute |
| Wind direction | Wind Dir AVG (S) 10M M1M | degrees | 1 minute |

Timestamps carry +08:00 (Singapore time). Stored as UTC and local time.

Temperature and wind speed are stored at full 1-minute detail (changed 11 November 2026). The plan on 10 November was one snapshot per hour, to stay inside the keyless rate limit of the current (v2) endpoint. The older v1 endpoint (`https://api.data.gov.sg/v1/environment/<variable>?date=YYYY-MM-DD`) returns a whole day in one response, so every reading fits in the same time. Its values are identical to v2: on 2024-03-01 all 18,069 shared rain readings and all 296 shared temperature readings were equal. Its day window leaves out the reading stamped 00:00, which is fetched with a second request (`date_time=YYYY-MM-DDT00:00:00`). Which minute or minutes are paired with a forecast is a matching rule in the verification protocol (section 3.3).

Rain stamps in 2024 fall on minutes 0, 5, ..., 55 with zero seconds. In the source check, days in January to April 2017 were stamped HH:M4:59 or HH:M9:59 instead (for example 23:59:59), and June 2017 onward used HH:M5:00. So the stamping convention changed in 2017. The provider does not say whether a stamp marks the start or the end of its 5 minutes. The hourly sum treats a stamp as the end of its interval, which the 2017 convention (one second before the next 5-minute mark) suggests. The planned check against the Changi airport record could not be run, because the airport reports hold almost no one-hour rain totals.

## Coverage

- From the collection metadata: rain from 2016-12-02, temperature 2016-05-05, humidity 2016-11-16, wind direction 2016-11-29, wind speed 2016-12-08.
- Rain: 54 to 80 gauges reported in each year from 2017 to 2025, and 91 in 2026 after the network grew.
- Temperature: 16 to 21 stations a year to 2025, and 35 in 2026. Wind speed: 15 to 21 stations a year.
- In the sample week, 81.7 percent of gauge-days had all 288 readings. The median was 288 and the worst gauge-day had 15.

## How it fails

| Failure | What it looks like in the data | How often here | Check that catches it |
|---|---|---|---|
| Bucket size differs between gauges | 19 gauges (S203 to S229) report multiples of their own tip, from 0.197 to 0.204 mm. The other 44 report exact multiples of 0.2 mm. Each gauge is consistent. | 19 of 63 gauges | Not a fault. Recorded per gauge so a "one tip" rain threshold works for all |
| Missing readings | Fewer than 288 five-minute readings in a day | 18.3 percent of gauge-days in the sample week. Over 11 February 2024 to 31 December 2025, 99.17 percent of station-hours with any reading had all 12 | Count per hour; hours below the protocol's completeness limit are dropped |
| Gauge stuck dry (blocked funnel) | Zero for an hour while the gauges within 10 km have a median of 5 mm or more | 1,850 gauge-hours, 2017 to 2026 | `stuck_dry` |
| Repeated non-zero value | Same non-zero 5-minute total for an hour or more | 2,191 readings, 2017 to 2026 | `flatline` (zero ignored) |
| Impossible value | Negative, or above 30 mm in 5 minutes | 1 reading, 2017 to 2026 | `range` |
| Duplicate stamps | Same gauge and time twice | None, 2017 to 2026 | `duplicate` |
| Undercatch in wind and very intense rain | Lower totals than the true rain. Cannot be seen from the gauge alone | Not measured | None. Stated as a limit |
| Temperature sensor spike, flatline, clock shift | A jump of 3 degrees from both neighbours; the same reading for two hours; the warmest hour of a month outside 11:00 to 17:00 | 383 spikes, 23,652 frozen readings and 5 station-months with the warmest hour at 10:00 or 18:00, 2017 to 2026 | `spike`, `flatline`, `timezone` |

## What it cannot see

- Rain that falls between gauges. Singapore convection is often a few kilometres across.
- Rain below one tip (about 0.2 mm) in a 5-minute step: it carries over to a later step.
- Undercatch in strong wind, which is usual in squalls.

## Effect on scores

Removing the flagged readings changes no one-day-ahead mean absolute error by more than 0.001 (mm, °C or m/s), and no paired comparison with climatology at three decimals. The checks matter more than that suggests, because most flags fall in the climatology years, 2017 to 2023: there they keep stuck and frozen sensors out of the free baseline. In the test period they remove 577 rain station-hours, 97 temperature and 4 wind station-hours at lead day 1. Both versions of every table are in `data/tables/results/results.parquet` (column `qc`).

## Sources

- data.gov.sg collection 1459 metadata: `https://api-production.data.gov.sg/v2/public/api/collections/1459/metadata`
- Developer guide and rate limits: https://guide.data.gov.sg/developer-guide/api-overview/api-rate-limits
- Raw evidence: `data/raw/datagovsg/`, probes in `data/raw/probe/`, check results in `docs/source_check.md`
