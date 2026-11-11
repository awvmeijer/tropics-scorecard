# Data source check

Run on 10 November 2026 with real requests. Raw responses are in `data/raw/probe/` (not committed). Reference point for forecast requests: Changi, 1.3679 N, 103.9824 E.

## Observations

### data.gov.sg, collection 1459 (Realtime Weather Readings across Singapore)

- Endpoint: `https://api-open.data.gov.sg/v2/real-time/api/<variable>` with `<variable>` one of `rainfall`, `air-temperature`, `relative-humidity`, `wind-speed`, `wind-direction`.
- Date parameter: `date=YYYY-MM-DD` returns the whole day, newest first, 25 readings per page. `date=YYYY-MM-DDTHH:MM:SS` returns one snapshot.
- Pagination: `paginationToken` in the response, passed back as a query parameter. Confirmed on page 2.
- Coverage start from the collection metadata: air temperature 2016-05-05, relative humidity 2016-11-16, wind direction 2016-11-29, rainfall 2016-12-02, wind speed 2016-12-08. Requests for June 2016 returned "Data not found" for rain, humidity and wind.
- Rain: unit mm, reading type "TB1 Rainfall 5 Minute Total F", 5-minute totals, 47 to 67 stations depending on year. One day is about 12 pages.
- Temperature, humidity, wind: 1-minute readings, 11 to 16 stations. Wind speed is in knots ("AVG(S)10M M1M"), direction in degrees. One day is about 58 pages per variable.
- Timestamps carry +08:00 (Singapore time).
- Access: no key needed, but requests without a key are rate limited to roughly one every 7 to 10 seconds (HTTP 429 otherwise). The default Python User-Agent gets HTTP 403; a named client works.
- Bulk download: none. The collection is API only.
- Older v1 endpoint, checked 2026-11-11: `https://api.data.gov.sg/v1/environment/<variable>?date=YYYY-MM-DD` returns every reading of the day in one response (rain 287 readings per gauge, temperature 1,438 per station on 2024-03-01), with no pagination. The window leaves out the reading stamped 00:00; `date_time=YYYY-MM-DDT00:00:00` returns it. Values match v2 exactly. No HTTP 429 at one request every 2 seconds. Rain back to 2017 and temperature and wind at 1-minute detail now cost two requests per day per variable instead of 12 to 58.

### NOAA Integrated Surface Database, global hourly

- The NCEI path `ncei.noaa.gov/data/global-hourly/access/` now redirects (HTTP 301) to the AWS open data bucket `https://noaa-global-hourly-pds.s3.amazonaws.com/<year>/<USAF><WBAN>.csv`.
- Layout: one CSV per station per year, columns STATION, DATE (UTC), REPORT_TYPE, WND, TMP, DEW, SLP, AA1 to AA3 (precipitation) and others.
- Stations in the bounding box: Changi 48698099999, Paya Lebar 48694099999, Seletar 48699099999, Senai 48679099999, Mersing 48602199999, Batam Hang Nadim 96087099999, Kijang 96091099999. Kuala Lumpur is outside the bounding box (about 101.7 E).
- **The archive stops on 2025-08-24.** The bucket has no 2026 folder, and the station history file lists 2025-08-24 as the end date for every station in the region (Batam ends 2025-03-07).
- Rain at airports is weak: at Changi in 2024 almost every AA1 record has period code 99 (unknown) or 24 hours; only 8 records were 1-hour totals. ISD is usable for temperature and wind, not for hourly rain.

### Integrated Global Radiosonde Archive, version 2

- Changi is `SNM00048698` (1.3679 N, 103.9824 E), listed 1955 to 2026.
- Files: `.../integrated-global-radiosonde-archive/access/data-y2d/SNM00048698-data-beg2026.txt.zip` (current year) and `.../data-por/SNM00048698-data.txt.zip` (period of record).
- 2026 so far: 592 soundings from 2026-01-01 00 UTC to 2026-11-08 11 UTC. Nominal hours are 00 and 12 UTC, but 267 of the evening soundings are stamped 11 UTC and 15 are stamped 12 UTC.

## Forecasts (Open-Meteo)

Model identifiers, accepted by the API (an unknown identifier returns an error): `ecmwf_ifs` (IFS HRES 9 km), `ecmwf_ifs025` (IFS 0.25), `ecmwf_aifs025_single` (AIFS 0.25), `gfs_global` (also accepted as `ncep_gfs_global`), `gfs_seamless`. `gfs025` is accepted but returned no data in Previous Runs.

### Previous Runs, first valid hour with data

| Model | Lead day 1 from | Lead day 7 from | Missing hours after that, days 1/3/7 |
|---|---|---|---|
| gfs_global | 2024-01-19 12 UTC | 2024-01-25 12 UTC | none |
| ecmwf_ifs025 | 2024-02-04 | 2024-02-10 | none, except day 7 rain: 129 hours in April 2026 |
| ecmwf_aifs025_single | 2025-02-18 | 2025-02-24 | day 7 temperature: 318 hours in April 2026 |
| ecmwf_ifs (9 km) | 2025-10-01 | 2025-10-07 | 3 to 7 percent, all in March to May 2026 |

The brief's "most models from January 2024" is not right for ECMWF: IFS 0.25 starts in February 2024, and IFS HRES 9 km in Previous Runs only starts in October 2025. GFS temperature does exist before 2024 (non-empty in June 2021 and June 2023); GFS rain and wind do not.

### Single Runs

- `run=YYYY-MM-DDTHH:MM`, default length 7 days (168 hours). Unavailable runs return "The requested model run is not available".
- `ecmwf_ifs`: run 2024-03-14 00 UTC exists, 2024-03-13 does not. Confirmed.
- `gfs_global` and `ecmwf_ifs025`: run 2026-04-02 exists, 2026-04-01 does not. Confirmed.
- `ecmwf_aifs025_single`: 2026-09-01 run exists; start date not probed.
- Precipitation is null at the run's first hour, so the hourly value labels the hour ending at that time.

### Historical Forecast, first data

`ecmwf_ifs` 2017-01-01, `gfs_global` 2021-03-23, `ecmwf_ifs025` 2024-02-03, `ecmwf_aifs025_single` 2025-02-17. In February 2024 `ecmwf_ifs025` rain had fewer non-null hours than temperature (527 against 768), so its rain may not be hourly in that period.

### Terms

- Free API: non-commercial use, under 10,000 calls a day, 5,000 an hour and 600 a minute. A request with more than 10 variables or more than 2 weeks counts as more than one call, pro rata.
- Data licence CC BY 4.0. Attribution must link next to where the data is shown, for example "Weather data by Open-Meteo.com" linking to https://open-meteo.com/, and state any changes made.
