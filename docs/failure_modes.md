# Failure-mode log

One row per failure found in a case study or in the stratified scores. A failure is a pattern, not a single bad forecast.

| Date found | Forecast source | What went wrong | Conditions | Evidence | Likely physical reason | How sure |
|---|---|---|---|---|---|---|
| 2026-11-13 | GFS, rain, lead days 5 and 7 | Archived rain averages 0.11 to 0.14 mm an hour against 0.32 at lead day 1, while the share of wet hours stays at one third. The low error at these leads came from forecasting a third of the rain, not from skill | Every hour beyond 120 hours into a run, where GFS output changes from hourly to 3-hourly steps | Mean forecast rain by lead for the Singapore cells; 57 percent of wet hours repeat the hour before at day 7, against 8 percent at day 1 | Not physical: the 3-hourly totals appear to be divided by three once too often somewhere between the model and the archive | High that the values are wrong, low on where. Excluded from scoring (config `exclusions`) |
| 2026-11-13 | ECMWF IFS 0.25 and AIFS, hourly rain | Rain is spread evenly over 3 or 6 hours, so the forecast says light rain in many hours where the gauges are dry: false alarm ratio near 0.9 at 0.1 mm, and AIFS says rain in 69 to 82 percent of hours | All hours, all leads | 70 to 87 percent of wet forecast hours equal the hour before | Not physical: the public output of these models has 3-hour or 6-hour steps, and the archive fills the hours between | High. Hourly rain occurrence is an unfair test for these two; a 6-hour total would be the fair one |
