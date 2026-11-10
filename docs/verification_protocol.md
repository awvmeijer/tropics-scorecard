# Verification protocol

Written before any scoring. Changed only with a dated note at the bottom saying what changed and why.

## 1. The decisions these scores should inform

Who would use this forecast, and for what? Write two or three concrete decisions. Each metric below must trace back to one of them.

## 2. Reference

The reference is the station observation after quality control. Not a reanalysis.

- How is observation error treated?
- A gauge is a point and a forecast is a grid cell. What does that do to each variable, and how is it stated on the results?

## 3. Matching

- Grid point: nearest, or interpolated? Why?
- Time: is a forecast hour the start, the end, or the centre of its interval? Same question for each observation source.
- Accumulations: how are sub-hourly gauge readings summed to match the forecast step?
- Missing values: what fraction of an hour may be missing before the hour is dropped?

## 4. Variables, thresholds and metrics

| Variable | Question | Metric | Threshold | Why this one |
|---|---|---|---|---|
| Hourly rain occurrence | | | | |
| Hourly rain amount | | | | |
| Temperature at 2 m | | | | |
| Wind speed at 10 m | | | | |

## 5. Baselines

- Persistence: defined how, for each variable?
- Climatology: by hour of day and month, from which years? Do those years overlap the test period?

## 6. Stratification

- Lead time bins
- Hour of day, local time
- Monsoon phase: dates used, and the source for them

## 7. Uncertainty

- Paired differences against the baseline on the same cases
- Block length for the bootstrap, and how it was chosen
- Number of resamples and the interval level
- What counts as "no detectable difference"

## 8. What this protocol cannot tell you

Write the limits here before seeing results.

## Change log

| Date | Change | Reason |
|---|---|---|
