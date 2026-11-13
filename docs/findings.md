# Findings

Status: draft, 13 November 2026. Written from the first full scoring run, for the author to review and put in his own words. Every number is at lead day 1 unless it says otherwise, on valid times from 11 February 2024 to 31 October 2026, and traces to `data/tables/results/results.parquet` (shown on the dashboard). Intervals are 95 percent, from a moving-block bootstrap over days with 8-day blocks.

1. **For hourly rain, ECMWF IFS 0.25 beats both free baselines at every lead out to seven days, but not by much.** Its mean absolute error (MAE) is 0.064 mm lower than climatology at day 1 (interval 0.042 to 0.085 lower) and 0.030 lower at day 7 (0.010 to 0.054). GFS shows no detectable difference from persistence or climatology at day 1, and is better than both at days 2 and 3.
2. **Over six hours the picture holds, and one model changes place.** On 6-hour totals ECMWF IFS 0.25 beats climatology by 0.375 mm at day 1 (0.254 to 0.499), about 13 percent of climatology's error, against 12 percent hourly. The gain is largest for ECMWF AIFS (0.608 mm, 0.461 to 0.769), whose public output has 6-hour steps and cannot be judged fairly hour by hour.
3. **No model beats climatology for temperature at a station.** GFS is 0.153 degrees C worse (0.099 to 0.206) and ECMWF IFS 0.25 is 0.239 worse (0.185 to 0.293). Both read too cool, by 0.6 and 0.9 degrees, and for IFS the cool bias grows to 1.3 to 1.5 degrees between 09:00 and 15:00 local time. Only ECMWF AIFS shows no detectable difference from climatology (0.030 better, interval 0.090 better to 0.022 worse), on its shorter period.
4. **Wind at a station is forecast worse than "the usual for this hour and month".** Every model has a higher MAE than both baselines, by 0.29 to 0.80 metres per second, and every model reads too windy (0.4 to 1.2 metres per second). This is the point against grid cell mismatch more than a forecast failure: a 10 m wind over a 13 to 28 km cell, part of it sea, is not the wind at a sheltered urban mast.
5. **Which grid cell a station is paired with matters as much as which model is used.** Pairing with Open-Meteo's land cell instead of the cell the station sits in makes ECMWF IFS 0.25 temperature 0.450 degrees worse (0.421 to 0.482) and its wind 0.443 metres per second better (0.404 to 0.482). The difference between GFS and IFS on temperature is 0.086 degrees.

## Also found

- The afternoon is where rain error concentrates: for every source the hourly rain MAE is four to six times higher at 16:00 local time than at midnight, and both models forecast too little rain between 15:00 and 18:00 (IFS by 0.24 to 0.41 mm an hour) and slightly too much before dawn.
- Quality control changes the scores in the fourth decimal place. Every score was computed with and without flagged readings; the largest change in MAE at day 1 is 0.0004.
- The climatology for 2017 to 2023 is 0.31 degrees cooler than the test period. The test period was warmer than the seven years before it.
- Two faults in the forecast archive were found and are logged in `docs/failure_modes.md`: GFS rain beyond 120 hours (excluded), and the 3-hour and 6-hour steps of ECMWF rain (stated as a limit).
