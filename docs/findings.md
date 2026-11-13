# Findings

I asked one question: how close was the forecast to what the instruments in Singapore measured, and how sure can I be?

These are the answers. Every number is for a forecast made one day ahead unless I say otherwise. The test runs from 11 February 2024 to 31 October 2026. Each range in brackets is a 95 percent interval. If a range includes zero, I call it no detectable difference and leave it there.

## 1. For rain, the best forecast beats the free baselines, but only just

ECMWF's forecast is closer to the gauges than climatology at every lead time out to seven days. One day ahead its hourly error is 0.063 mm lower (0.041 to 0.085). Seven days ahead it is 0.029 mm lower (0.009 to 0.053). That is a gain of about 12 percent over "what usually happens at this hour, in this month".

GFS, one day ahead, is not detectably better than assuming tomorrow repeats today.

A forecast can be real and still be a small step up from something free. For hourly rain at a point in the tropics, that is where things stand.

## 2. No model beats climatology for temperature

This surprised me. At a weather station, "the usual temperature for this hour and month" is closer to the truth than GFS by 0.15 degrees C (0.10 to 0.21) and closer than ECMWF by 0.24 degrees (0.19 to 0.29).

Both models run cool. ECMWF is 1.2 to 1.5 degrees too cool between 9 in the morning and 3 in the afternoon, and about half that at night. I think I know why: on its grid, the cell that holds about half the stations is mostly sea. Sea does not heat up during the day the way a city does.

## 3. Wind at a station is forecast worse than a guess from history

Every model is further from the measured wind than both baselines, by 0.3 to 0.8 metres per second. Every model reads too windy.

I do not read this as the models failing at wind. A grid cell 9 to 28 km wide, part of it open water, is being compared with a mast between buildings. They are not measuring the same thing. But anyone who needs the wind at that mast should know the raw forecast does not give it to them.

## 4. Which grid cell you pick matters more than which model you pick

A station has to be paired with one cell of the model's grid. There are two sensible rules: take the cell the station sits in, or take the nearest cell the model treats as land. For ECMWF the land rule moves 73 of the 74 stations in the island's southern cells to a cell centred in Johor, in another country.

That one choice makes ECMWF's temperature 0.44 degrees worse (0.41 to 0.47) and its wind 0.44 metres per second better (0.40 to 0.48). The whole gap between GFS and ECMWF on temperature is 0.09 degrees.

I chose the cell the station sits in, before I saw any score, and I report the other as a check. A comparison that does not say which rule it used cannot be compared with anyone else's.

## 5. Two of my first results were faults in the data, not skill

On the first scoring run, GFS rain looked better seven days ahead than one day ahead. That cannot be right, so I looked. Beyond 120 hours, the archived GFS rain averages a third of its day-one amount, with the same number of wet hours. Forecasting a third of the rain lowers the error. I removed those lead times and wrote down why, even though it meant deleting a result that looked good.

The second fault runs the other way. ECMWF's public rain comes in 3-hour and 6-hour steps, spread evenly across the hours between. Scored hour by hour, that looks like drizzle that never fell. So I added a second rain test on 6-hour totals. There, ECMWF's AIFS, which looked poor hour by hour, cuts the 6-hour error by about a fifth against climatology one day ahead, on the shorter period it covers.

Both were found by asking why a number looked the way it did before believing it.

## 6. Across every lead time, the picture does not change

Published scorecards for learned weather models show every variable at every lead time as a grid: blue where the model beats the reference, red where it is worse. I built the same grid with two changes: the truth is the instruments, and the reference is climatology. Each cell is the change in error as a percentage of climatology's error on the same cases.

Rain is blue in 33 of 36 cells. Temperature and wind are blue in none of 40. So the one-day-ahead result in sections 1 to 3 is not a quirk of one lead time. The row closest to blue for temperature belongs to ECMWF's AIFS, a learned model: no worse than climatology over the first two days, then worse by 5 to 8 percent from day 3, on its shorter period.

## 7. The heaviest rain is about a third of what fell

The FourCastNet paper tests extremes by comparing a model's heaviest values with the heaviest observed: the relative quantile error. Against reanalysis, its authors found ECMWF's heaviest rain about 15 percent too light. I ran the same test on 6-hour totals against the gauges.

One day ahead, the heaviest 0.1 percent of 6-hour totals at single gauges is 76 mm. ECMWF's grid cell gives 22 mm. A point is not a cell, so I also averaged the gauges inside each cell, using only cell-times with at least five gauges. That brings the measured figure down to 67 mm, not to 22. ECMWF's heaviest totals are 67 percent too light (62 to 71). Its two other models are much the same: AIFS 63 percent (60 to 81), IFS 9 km 72 percent (58 to 81).

GFS is different at the very top. Its heaviest 0.1 percent is not detectably lighter than the gauges' (minus 52 to plus 71 percent). It does produce totals that heavy. It just rarely puts them in the right hour and place: it caught 1.6 percent of the hours with 10 mm or more. At the heaviest 1 percent, every model is too light, GFS included, by 51 to 69 percent.

So the point-against-cell mismatch explains only a small part of the gap for heavy rain. Most of it is the models.

## 8. Acted on, the forecasts keep little of what a perfect one would save

An error in millimetres does not say what a forecast is worth, so I scored a decision. Someone can protect against heavy rain at a cost, to avoid a bigger loss, and protects whenever the forecast says 10 mm or more. I compared what that costs them with the best fixed habit (always protect, or never) and with a perfect forecast. The share of the perfect forecast's saving they keep is the forecast's value.

For 6-hour totals one day ahead, GFS keeps at most 13 percent (5 to 18), when protecting costs about 5 percent of the loss it avoids. ECMWF keeps at most 6 percent (minus 4 to 10), not detectably above zero. Persistence, assuming tomorrow repeats today, keeps at most 9 percent (0 to 11). GFS has any value only when protecting costs between about 5 and 20 percent of the loss; outside that band, acting on it costs more than the best fixed habit. Hour by hour, with 10 mm in a single hour as the trigger, no forecast keeps more than 2 percent.

## 9. Judge the same forecasts by the reanalysis, and the verdict changes

ERA5 is the reanalysis most learned weather models are trained on and scored against. I added it two ways.

First, scored against the stations like any forecast. ERA5's temperature error is 10 percent larger than station climatology's (6 to 13), and it runs 0.6 degrees cool, even though observations went into it. Its wind error is about twice climatology's (94 to 115 percent larger), reading 1.4 metres per second too windy. For 6-hour rain its error is 13 percent smaller than climatology's (6 to 19), close to ECMWF's one-day forecast. Its heaviest 6-hour totals are 22 percent lighter than the gauges averaged over its cells (7 to 47): too light, but much less so than the forecasts.

Second, as the judge, on exactly the same station-hours, with an ERA5 climatology from the same years as the free guess. Of the 76 cells in the scorecard, 31 change colour. For temperature one day ahead, GFS's error is 6 percent lower than ECMWF's (3 to 10) against the instruments, and 39 percent higher (36 to 42) against ERA5: the two models swap places. ECMWF's AIFS, a learned model trained on ERA5 and then on ECMWF's own analyses, beats climatology for temperature at every lead day when ERA5 is the judge, by 9 to 17 percent, and at none when the instruments are. The 9 km IFS, the finest model here, looks worst for temperature and wind when ERA5's 28 km cells are the judge.

ERA5 does what it is built to do: estimate the weather over a 28 km cell. A model trained and scored against it learns to match that cell, not the instruments inside it, and here the two disagree most for temperature and wind at the surface.

I added sections 6 to 9 after the main scoring, and the protocol log says so. The scorecard and the extremes test follow published methods, and the decision score is the standard cost-loss value. The two percentiles and the five-gauge minimum were picked during a first look at the numbers, so treat them as a check rather than a test fixed in advance.

## What the case studies add

- **A monsoon surge in the wettest March on record, 2025.** Both models warned of it days ahead. The amount was another matter: 268 mm fell, GFS said 207, ECMWF said 121.
- **A squall line, 17 September 2024.** Thirty-one of 62 gauges took 10 mm or more in a single hour. No forecast had it, at any lead time.
- **An 18-day dry spell, July 2024.** 1.6 mm fell. GFS forecast 81 mm, with showers on most afternoons that never came.

The gauges alone found that dry spell on the same dates as the official record, to the day. That was my check that the observation side is right.

## What I am not claiming

A rain gauge is a point and a forecast is an average over a grid cell. Part of every low score is that mismatch. The test is under three years, so each monsoon season appears two or three times. The forecasts come from a public archive, and I have already found two faults in it. This is one region and one set of archives, not a ranking of models.

Every number here traces to a table in the repository. The rules were written down before the scoring, and everything added later is marked in the change log of [verification_protocol.md](verification_protocol.md).
