# Observation note: airport reports (NOAA Integrated Surface Database)

Status: first draft, 10 November 2026. Based on all reports from seven airports, 2017 to 2025.

## What it measures

Airport weather reports, decoded by NOAA into one CSV per station per year. Times are UTC.

- Temperature and dewpoint, wind direction and speed, sea-level pressure, and sometimes rain over a stated period.
- Report types seen: FM-12 (SYNOP, on the hour), FM-15 (METAR, on the hour and at half past), FM-16 (special METAR).
- A report is a snapshot at its time, not an average over the hour, except the 10-minute mean wind.

## Coverage

| Station | ISD id | Preferred hourly reports, 2024 |
|---|---|---|
| Singapore Changi | 48698099999 | 8,425 |
| Paya Lebar | 48694099999 | 8,367 |
| Seletar | 48699099999 | 8,390 |
| Senai | 48679099999 | 8,401 |
| Mersing | 48602199999 | 8,378 |
| Batam Hang Nadim | 96087099999 | 3,204 (about every 3 hours) |
| Kijang | 96091099999 | 3,964 (3-hourly until 2024, near hourly in 2025) |

**The archive ends on 2025-08-24** for every station here (Batam on 2025-03-07). It covers the first 18 months of the study period and none of 2026.

## How it fails

| Failure | What it looks like in the data | How often here | Check that catches it |
|---|---|---|---|
| Two reports for one hour | A SYNOP and a METAR at the same hour with different values. Not an error: the METAR rounds temperature to whole degrees and wind to whole knots | Every hour at the Singapore airports. At Changi in 2024, the METAR minus SYNOP temperature had mean -0.13 and standard deviation 0.53 deg C | Store keeps both; `preferred` picks the SYNOP, then the METAR, then a special report. Half-hour METARs are never preferred |
| Rounding | METAR wind speeds come only as 1.0, 1.5, 2.1, 2.6, 3.1 m/s and so on (whole knots). METAR temperatures are 100 percent whole degrees | All METARs | None needed. Stated so the reader knows the resolution |
| Bad ISD quality code | Codes 2, 3, 6 or 7 on the value | 140 temperature and 12 wind values, 2017 to 2025 | `isd_quality_code` |
| Temperature spike | One reading 5 to 12 deg C away from both neighbours. Some may be real: for example Senai at 05 UTC on 7 September 2024 reads 27.0 between 32.0 and 32.1, which a passing storm could cause | 24 preferred reports, 2017 to 2025 | `spike` (4 deg C, neighbours within 90 minutes). Flagged, not deleted |
| Clock error | Warmest hour of the month outside 11:00 to 17:00 local | None found | `timezone` |
| Hourly rain missing | Rain appears only as 3, 6 or 24 hour totals, or with an unknown period | Only 6,129 one-hour totals across all stations and years | Not used for hourly rain scoring |
| Light and variable winds | Direction type "V" (variable) on 38.9 percent of preferred reports, calm on 9.2 percent | | Direction not scored when variable |

## What it cannot see

- Rain between reports, and rain at all for most hours.
- Anything after 2025-08-24.
- Conditions away from the runway; all seven sites are open airfields, unlike the urban data.gov.sg sites.

## Effect on scores

To be filled after the scores are computed with and without flags. ISD covers only part of the study period, so its scores will be reported for that part alone.

## Sources

- Bucket: https://noaa-global-hourly-pds.s3.amazonaws.com/ (NCEI's global-hourly path redirects there)
- Station list: https://www.ncei.noaa.gov/pub/data/noaa/isd-history.csv
- Field definitions: the ISD format document published by NCEI
