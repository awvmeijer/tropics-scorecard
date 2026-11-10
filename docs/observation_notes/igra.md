# Observation note: Changi radiosonde (Integrated Global Radiosonde Archive, version 2)

Status: first draft, 10 November 2026. Based on soundings from 2021 to 8 November 2026 unless stated.

## What it measures

A balloon-borne sonde launched from Changi (IGRA id SNM00048698, 1.3679 N, 103.9824 E). Each sounding lists levels with pressure, height, temperature, dewpoint depression, wind direction and speed, and time since launch. Relative humidity at the surface is missing on every sounding; humidity is given as dewpoint depression (present on 99.9 percent of surface levels).

The header gives a nominal hour and a release time, both UTC. The nominal hour is not the launch time:

| Nominal hour (UTC) | Soundings | Median release relative to nominal |
|---|---|---|
| 00 | 2,065 | 25 minutes before (released about 23:35 the day before) |
| 11 | 1,716 | 18 minutes before |
| 12 | 187 | 45 minutes before |
| 10 | 156 | 26 minutes after |

The 06 and 18 UTC soundings carry a release time equal to the nominal time, which looks like a filled default, not a measured time.

## Coverage

- Four soundings a day (00, 06, 12, 18 UTC) from 2017 to 2020, about 1,460 a year.
- Two a day from 2021: 705 to 715 a year, 944 in 2023, 592 in 2026 up to 8 November.
- The evening sounding is usually stamped 11 UTC (1,716 times since 2021), not 12 UTC.
- Median 119 levels per sounding.

## How it fails

| Failure | What it looks like in the data | How often here | Check that catches it |
|---|---|---|---|
| Balloon drift | Not visible directly: IGRA v2 has no position per level. Integrating the reported wind over time since launch gives the drift | Median 6.0 km by 300 hPa, 90th percentile 10.9 km, largest 37.3 km (3,927 soundings) | None; stated on every case page that uses a sounding |
| Nominal time is not launch time | See the table above | Every sounding | Use release time where present |
| Missing surface humidity | RH -9999 at the surface level | Every sounding | Use dewpoint depression |
| Quality flags | A letter after pressure, height and temperature (B seen so far); meanings to be checked against the format document | Not yet counted | To add: count flags per variable |

## What it cannot see

- One point, twice a day. Afternoon convection develops between the 00 and 11 UTC launches (08:00 and 19:00 local).
- The air over the island interior: the sonde drifts several kilometres, usually away from Changi.

## Effect on scores

Soundings are not scored. They are used in case studies to describe the atmosphere before an event.

## Sources

- Station list: https://www.ncei.noaa.gov/data/integrated-global-radiosonde-archive/doc/igra2-station-list.txt
- Data: https://www.ncei.noaa.gov/data/integrated-global-radiosonde-archive/access/data-por/SNM00048698-data.txt.zip
- Format: the IGRA v2 data format description in the same `doc/` folder
