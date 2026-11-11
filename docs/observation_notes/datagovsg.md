# Observation note: Singapore station network (data.gov.sg, collection 1459)

Status: first draft, 10 November 2026, updated 11 November. Rain facts in the failure table come from 7 days (4 to 10 February 2024, 63 gauges, 124,768 readings) unless marked. Numbers are rechecked when the downloads complete. Humidity and wind direction are not downloaded.

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

Rain stamps in 2024 fall on minutes 0, 5, ..., 55 with zero seconds. In the source check, days in January to April 2017 were stamped HH:M4:59 or HH:M9:59 instead (for example 23:59:59), and June 2017 onward used HH:M5:00. So the stamping convention changed in 2017. The provider does not say whether a stamp marks the start or the end of its 5 minutes. **Not yet confirmed.** For now the hourly sum treats a stamp as the end of its interval, which the 2017 convention (one second before the next 5-minute mark) suggests. Comparing hourly sums both ways against the Changi airport record is the planned test.

## Coverage

- From the collection metadata: rain from 2016-12-02, temperature 2016-05-05, humidity 2016-11-16, wind direction 2016-11-29, wind speed 2016-12-08.
- Rain: 47 gauges in 2017, 67 in 2021 and 2023, 63 in the sample week.
- Temperature, humidity and wind: 11 to 16 stations.
- In the sample week, 81.7 percent of gauge-days had all 288 readings. The median was 288 and the worst gauge-day had 15.

## How it fails

| Failure | What it looks like in the data | How often here | Check that catches it |
|---|---|---|---|
| Bucket size differs between gauges | 19 gauges (S203 to S229) report multiples of their own tip, from 0.197 to 0.204 mm. The other 44 report exact multiples of 0.2 mm. Each gauge is consistent. | 19 of 63 gauges | Not a fault. Recorded per gauge so a "one tip" rain threshold works for all |
| Missing readings | Fewer than 288 five-minute readings in a day | 18.3 percent of gauge-days in the sample week. Over 11 February 2024 to 31 December 2025, 99.17 percent of station-hours with any reading had all 12 | Count per hour; hours below the protocol's completeness limit are dropped |
| Gauge stuck dry (blocked funnel) | Zero for an hour while nearby gauges record a lot | Not yet measured | `stuck_dry`, **blocked**: needs `metrics.geo.haversine_km` |
| Repeated non-zero value | Same non-zero 5-minute total for an hour or more | None in the sample week | `flatline` (zero ignored) |
| Impossible value | Negative, or above 30 mm in 5 minutes | None in the sample week (largest 11.4 mm) | `range` |
| Duplicate stamps | Same gauge and time twice | None in the sample week | `duplicate` |
| Undercatch in wind and very intense rain | Lower totals than the true rain. Cannot be seen from the gauge alone | Not measured | None. Stated as a limit |
| Temperature sensor spike, flatline, clock shift | To check once temperature is downloaded | | `spike`, `flatline`, `timezone` |

## What it cannot see

- Rain that falls between gauges. Singapore convection is often a few kilometres across.
- Rain below one tip (about 0.2 mm) in a 5-minute step: it carries over to a later step.
- Undercatch in strong wind, which is usual in squalls.

## Effect on scores

To be filled after the scores are computed with and without flags.

## Sources

- data.gov.sg collection 1459 metadata: `https://api-production.data.gov.sg/v2/public/api/collections/1459/metadata`
- Developer guide and rate limits: https://guide.data.gov.sg/developer-guide/api-overview/api-rate-limits
- Raw evidence: `data/raw/datagovsg/`, probes in `data/raw/probe/`, check results in `docs/source_check.md`
