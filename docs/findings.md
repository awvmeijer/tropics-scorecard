# Findings

I asked one question: how close was the forecast to what the instruments in Singapore measured, and how sure can I be?

These are the answers so far. Every number is for a forecast made one day ahead unless I say otherwise. The test runs from 11 February 2024 to 31 October 2026. Each range in brackets is a 95 percent interval. If a range includes zero, I call it no detectable difference and leave it there.

## 1. For rain, the best forecast beats the free baselines, but only just

ECMWF's forecast is closer to the gauges than climatology at every lead time out to seven days. One day ahead its hourly error is 0.064 mm lower (0.042 to 0.085). Seven days ahead it is 0.030 mm lower (0.010 to 0.054). That is a gain of about 12 percent over "what usually happens at this hour, in this month".

GFS, one day ahead, is not detectably better than assuming tomorrow repeats today.

A forecast can be real and still be a small step up from something free. For hourly rain at a point in the tropics, that is where things stand.

## 2. No model beats climatology for temperature

This surprised me. At a weather station, "the usual temperature for this hour and month" is closer to the truth than GFS by 0.15 degrees C (0.10 to 0.21) and closer than ECMWF by 0.24 degrees (0.19 to 0.29).

Both models run cool. ECMWF is 1.3 to 1.5 degrees too cool between 9 in the morning and 3 in the afternoon, and about half that at night. I think I know why: on its grid, the cell that holds most of Singapore is mostly sea. Sea does not heat up during the day the way a city does.

## 3. Wind at a station is forecast worse than a guess from history

Every model is further from the measured wind than both baselines, by 0.3 to 0.8 metres per second. Every model reads too windy.

I do not read this as the models failing at wind. A grid cell 13 to 28 km wide, part of it open water, is being compared with a mast between buildings. They are not measuring the same thing. But anyone who needs the wind at that mast should know the raw forecast does not give it to them.

## 4. Which grid cell you pick matters more than which model you pick

A station has to be paired with one cell of the model's grid. There are two sensible rules: take the cell the station sits in, or take the nearest cell the model treats as land. For ECMWF the land rule moves 53 of Singapore's 54 southern stations to a cell centred in Johor, in another country.

That one choice makes ECMWF's temperature 0.45 degrees worse (0.42 to 0.48) and its wind 0.44 metres per second better (0.40 to 0.48). The whole gap between GFS and ECMWF on temperature is 0.09 degrees.

I chose the cell the station sits in, before I saw any score, and I report the other as a check. A comparison that does not say which rule it used cannot be compared with anyone else's.

## 5. Two of my first results were faults in the data, not skill

On the first scoring run, GFS rain looked better seven days ahead than one day ahead. That cannot be right, so I looked. Beyond 120 hours, the archived GFS rain averages a third of its day-one amount, with the same number of wet hours. Forecasting a third of the rain lowers the error. I removed those lead times and wrote down why, even though it meant deleting a result that looked good.

The second fault runs the other way. ECMWF's public rain comes in 3-hour and 6-hour steps, spread evenly across the hours between. Scored hour by hour, that looks like drizzle that never fell. So I added a second rain test on 6-hour totals. There, ECMWF's newer AI model, which looked poor hour by hour, is among the best, on the shorter period it covers.

Both were found by asking why a number looked the way it did before believing it.

## 6. Across every lead time, the picture does not change

Published scorecards for learned weather models show every variable at every lead time as a grid: blue where the model beats the reference, red where it is worse. I built the same grid with two changes: the truth is the instruments, and the reference is climatology. Each cell is the change in error as a percentage of climatology's error on the same cases.

Rain is blue in 33 of 36 cells. Temperature and wind are blue in none of 40. So the one-day-ahead result in sections 1 to 3 is not a quirk of one lead time. The cell closest to blue for temperature belongs to ECMWF's AIFS, a learned model: no worse than climatology over the first three days, then worse by 6 to 8 percent at days 5 and 7, on its shorter period.

## 7. The heaviest rain is about a third of what fell

The FourCastNet paper tests extremes by comparing a model's heaviest values with the heaviest observed: the relative quantile error. Against reanalysis, its authors found ECMWF's heaviest rain about 15 percent too light. I ran the same test on 6-hour totals against the gauges.

One day ahead, the heaviest 0.1 percent of 6-hour totals at single gauges is 76 mm. ECMWF's grid cell gives 22 mm. A point is not a cell, so I also averaged the gauges inside each cell, using only cell-times with at least five gauges. That brings the measured figure down to 68 mm, not to 22. ECMWF's heaviest totals are 68 percent too light (62 to 71). Its two other models are much the same: AIFS 63 percent (59 to 81), IFS 9 km 72 percent (60 to 80).

GFS is different at the very top. Its heaviest 0.1 percent is not detectably lighter than the gauges' (minus 49 to plus 83 percent). It does produce totals that heavy. It just rarely puts them in the right hour and place: it caught 1.6 percent of the hours with 10 mm or more. At the heaviest 1 percent, every model is too light, GFS included, by 51 to 68 percent.

So the point-against-cell mismatch explains only a small part of the gap for heavy rain. Most of it is the models.

## 8. Acted on, the forecasts keep little of what a perfect one would save

An error in millimetres does not say what a forecast is worth, so I scored a decision. Someone can protect against heavy rain at a cost, to avoid a bigger loss, and protects whenever the forecast says 10 mm or more. I compared what that costs them with the best fixed habit (always protect, or never) and with a perfect forecast. The share of the perfect forecast's saving they keep is the forecast's value.

For 6-hour totals one day ahead, GFS keeps at most 13 percent (4 to 18), when protecting costs about 5 percent of the loss it avoids. ECMWF keeps at most 6 percent (minus 6 to 10), not detectably above zero. Persistence, assuming tomorrow repeats today, keeps 9 percent (0 to 11). GFS is worth anything only when protecting costs between 5 and 20 percent of the loss; outside that band, acting on it costs more than the best fixed habit. Hour by hour, with 10 mm in a single hour as the trigger, no forecast keeps more than 2 percent.

## 9. Judge the same forecasts by the reanalysis, and the verdict changes

ERA5 is the reanalysis most learned weather models are trained on and scored against. I added it two ways.

First, scored against the stations like any forecast. ERA5 itself is 10 percent further from the thermometers than station climatology (6 to 13), and runs 0.6 degrees cool, even though thermometer readings went into it. For wind it is 104 percent further (94 to 115), reading 1.4 metres per second too windy. For 6-hour rain it is 13 percent closer than climatology (6 to 19), about what ECMWF's one-day forecast achieves. Its heaviest 0.1 percent of 6-hour totals is 52 mm against 67 mm in the gauges averaged over the same cell: too light, but much less so than the forecasts.

Second, as the judge, on exactly the same station-hours, with an ERA5 climatology from the same years as the free guess. 31 of the 76 cells in the scorecard change colour. For temperature one day ahead, GFS's error is 6 percent lower than ECMWF's (3 to 9) against the instruments, and 40 percent higher (37 to 43) against ERA5: the order of the two models flips. ECMWF's AIFS, a learned model trained on ERA5 and then on ECMWF's own analyses, beats climatology for temperature at every lead day when ERA5 is the judge, and at none when the instruments are. The 9 km IFS, the finest model here, looks worst for temperature and wind against ERA5's 28 km cells, likely because a coarse judge penalises detail it cannot see.

None of this makes ERA5 a poor product: it is a grid-cell estimate, which is what it is built to be. But a model trained and scored against it is being asked to match the grid, not the ground, and here the two disagree most for temperature and wind at the surface.

I added sections 6 to 9 after the main scoring, and the protocol log says so. Both follow published methods. The two percentiles and the five-gauge minimum were picked during a first look at the numbers, so treat them as a check rather than a test fixed in advance.

## What the case studies add

- **A record monsoon surge, March 2025.** Both models warned of it days ahead. The amount was another matter: 268 mm fell, GFS said 207, ECMWF said 121.
- **A squall line, 17 September 2024.** Thirty-one of 62 gauges took 10 mm or more in a single hour. No forecast had it, at any lead time.
- **An 18-day dry spell, July 2024.** 1.6 mm fell. GFS forecast 81 mm, with showers on most afternoons that never came.

The gauges alone found that dry spell on the same dates as the official record, to the day. That was my check that the observation side is right.

## What I am not claiming

A rain gauge is a point and a forecast is an average over a grid cell. Part of every low score is that mismatch. The test is under three years, so each monsoon season appears two or three times. The forecasts come from a public archive, and I have already found two faults in it. This is one region and one set of archives, not a ranking of models.

Every number here traces to a table in the repository, and the rules were written down before the scoring: [verification_protocol.md](verification_protocol.md).
