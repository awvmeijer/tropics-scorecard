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

## 4. Which grid cell you pick matters as much as which model you pick

A station has to be paired with one cell of the model's grid. There are two sensible rules: take the cell the station sits in, or take the nearest cell the model treats as land. For ECMWF the land rule moves 53 of Singapore's 54 southern stations to a cell centred in Johor, in another country.

That one choice makes ECMWF's temperature 0.45 degrees worse (0.42 to 0.48) and its wind 0.44 metres per second better (0.40 to 0.48). The whole gap between GFS and ECMWF on temperature is 0.09 degrees.

I chose the cell the station sits in, before I saw any score, and I report the other as a check. A comparison that does not say which rule it used cannot be compared with anyone else's.

## 5. Two of my first results were faults in the data, not skill

On the first scoring run, GFS rain looked better seven days ahead than one day ahead. That cannot be right, so I looked. Beyond 120 hours, the archived GFS rain averages a third of its day-one amount, with the same number of wet hours. Forecasting a third of the rain lowers the error. I removed those lead times and wrote down why, even though it meant deleting a result that looked good.

The second fault runs the other way. ECMWF's public rain comes in 3-hour and 6-hour steps, spread evenly across the hours between. Scored hour by hour, that looks like drizzle that never fell. So I added a second rain test on 6-hour totals. There, ECMWF's newer AI model, which looked poor hour by hour, is among the best, on the shorter period it covers.

Both were found by asking why a number looked the way it did before believing it.

## What the case studies add

- **A record monsoon surge, March 2025.** Both models warned of it days ahead. The amount was another matter: 268 mm fell, GFS said 207, ECMWF said 121.
- **A squall line, 17 September 2024.** Thirty-one of 62 gauges took 10 mm or more in a single hour. No forecast had it, at any lead time.
- **An 18-day dry spell, July 2024.** 1.6 mm fell. GFS forecast 81 mm, with showers on most afternoons that never came.

The gauges alone found that dry spell on the same dates as the official record, to the day. That was my check that the observation side is right.

## What I am not claiming

A rain gauge is a point and a forecast is an average over a grid cell. Part of every low score is that mismatch. The test is under three years, so each monsoon season appears two or three times. The forecasts come from a public archive, and I have already found two faults in it. This is one region and one set of archives, not a ranking of models.

Every number here traces to a table in the repository, and the rules were written down before the scoring: [verification_protocol.md](verification_protocol.md).
