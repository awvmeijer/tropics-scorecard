# Findings

I asked one question: how close was the forecast to what the instruments in Singapore measured, and how sure can I be?

These are the answers. Every number is for a forecast made one day ahead unless I say otherwise, and every error is a root mean square error unless I name another. The test runs from 11 February 2024 to 31 October 2026. Each range in brackets is a 95 percent interval. If a range includes zero, I call it no detectable difference and leave it there.

## 1. Against the instruments, the raw forecasts lose to a free guess

Climatology is the forecast you get for free: what usually happens at this station, in this month, at this hour. I scored every model against it by root mean square error, at every lead day, the way published scorecards for learned weather models do, with one change: the truth is the instruments.

Of 76 cells in that grid, a forecast is detectably better than climatology in 7. All 7 belong to ECMWF's AIFS, the learned model, on its shorter archive: 6-hour rain on days 1 to 3 (6, 6 and 4 percent better), hourly rain on days 1 to 3 (1 to 2 percent), and temperature on day 1 (4 percent, 0.3 to 9). GFS and ECMWF's IFS are better nowhere.

Temperature is worse than climatology in 17 of 20 cells and wind in all 20. One day ahead, GFS's temperature error is 14 percent larger (10 to 17) and ECMWF's 18 percent larger (14 to 21). Both run cool. ECMWF is 1.2 to 1.5 degrees too cool between 9 in the morning and 3 in the afternoon, and about half that at night. I think I know why: on its grid, the cell that holds about half the stations is mostly sea, and sea does not heat up during the day the way a city does.

For wind, every model reads too windy, by 0.4 to 1.2 metres per second, and its error is 34 to 85 percent larger than climatology's. I do not read this as the models failing at wind. A grid cell 9 to 28 km wide, part of it open water, is being compared with a mast between buildings. But anyone who needs the wind at that mast should know the raw forecast does not give it to them.

## 2. For rain, the score you pick decides who wins

My first version of this study said ECMWF's rain beat climatology by 12 percent. It did, by mean absolute error: one day ahead its hourly error is 0.063 mm lower (0.041 to 0.085), and it stays lower out to seven days.

Then I scored a forecast that never rains. By mean absolute error, always-dry beats climatology by 47 percent hour by hour (46 to 49) and by 41 percent on 6-hour totals (39 to 43). It beats every model. Rain is zero most of the time, so the forecast that minimises absolute error is the median, which is zero, and any forecast that rains too little is rewarded for it. ECMWF's forecast is 12 percent too dry over the test. A score that a useless forecast wins cannot carry the headline, so I withdrew it.

Root mean square error punishes a missed downpour in proportion. By that score always-dry is 4 percent worse than climatology on 6-hour totals (3 to 6). ECMWF's IFS is no different from climatology (minus 4 to plus 4 percent), GFS is no different (minus 3 to plus 31), and the one forecast that beats it is AIFS, 6 percent better (1 to 15).

Root mean square error has its own trap: it rewards smooth forecasts that never commit to a heavy total, and a model trained to minimise squared error is smooth by construction. So neither score is safe alone. Sections 7 and 8 test the heavy rain and the decision directly, and both scores are kept in the tables.

## 3. A perfect forecast at this grid size would do far better

The usual defence of a low score at a gauge is that a point is not a grid cell. I measured how much that costs. For each gauge I built the forecast a perfect 0.25 degree model would give: the true mean of the other gauges in its cell, with the gauge itself left out, in cells with at least five gauges. It knows the cell's rain exactly and nothing finer.

Scored at the gauge it left out, on 6-hour totals, that forecast correlates 0.82 with the gauge and cuts root mean square error by 42 percent against climatology (27 to 68). ECMWF's one-day forecast, on the same 233,109 gauge-times, correlates 0.20 and is no different from climatology (minus 4 to plus 4 percent). Climatology itself correlates 0.16.

So the mismatch between a point and a cell explains part of the gap and not the rest. The gauges show why a cell forecast can do this well: two gauges under 2 km apart correlate 0.93 on 6-hour rain, 0.72 at 4 to 8 km, and 0.48 at 15 to 30 km. Rain a few kilometres away tells you most of what fell here.

One limit: the other gauges in a cell are not the true cell mean, only a sample of it, so the real ceiling could be a little higher or lower than 42 percent.

## 4. Which grid cell you pick matters more than which model you pick

A station has to be paired with one cell of the model's grid. There are two sensible rules: take the cell the station sits in, or take the nearest cell the model treats as land. For ECMWF the land rule moves 73 of the 74 stations in the island's southern cells to a cell centred in Johor, in another country.

That one choice makes ECMWF's mean absolute temperature error 0.45 degrees worse (0.42 to 0.48) and its wind error 0.43 metres per second better (0.38 to 0.47). The whole gap between GFS and ECMWF on temperature is 0.08 degrees.

I chose the cell the station sits in, before I saw any score, and I report the other as a check. A comparison that does not say which rule it used cannot be compared with anyone else's.

## 5. Two of my first results were faults in the data, not skill

On the first scoring run, GFS rain looked better seven days ahead than one day ahead. That cannot be right, so I looked. Beyond 120 hours, the archived GFS rain averages a third of its day-one amount, with the same number of wet hours. Forecasting a third of the rain lowers the mean absolute error, the same trap as in section 2. I removed those lead times and wrote down why, even though it meant deleting a result that looked good.

The second fault runs the other way. ECMWF's public rain comes in 3-hour and 6-hour steps, spread evenly across the hours between. Scored hour by hour, that looks like drizzle that never fell. So I added a second rain test on 6-hour totals.

Both were found by asking why a number looked the way it did before believing it.

## 6. Duplicate stations were being scored twice

Two airports appear in both observation sources: Changi and Paya Lebar report through the airport network and through Singapore's own station network. Their hourly temperatures agree to within 0.06 and 0.27 degrees on average, so they are the same instruments. Scoring both gave those two sites double weight. I now drop the airport-network copies and score 110 stations instead of 112. The scores moved little: ECMWF's rain and temperature comparisons with climatology are unchanged to the first decimal of a percent.

## 7. The heaviest rain is about a third of what fell

The FourCastNet paper tests extremes by comparing a model's heaviest values with the heaviest observed: the relative quantile error. Against reanalysis, its authors found ECMWF's heaviest rain about 15 percent too light. I ran the same test on 6-hour totals against the gauges.

One day ahead, the heaviest 0.1 percent of 6-hour totals at single gauges is 76 mm. ECMWF's grid cell gives 22 mm. A point is not a cell, so I also averaged the gauges inside each cell, using only cell-times with at least five gauges. That brings the measured figure down to 67 mm, not to 22. ECMWF's heaviest totals are 67 percent too light (62 to 71). Its two other models are much the same: AIFS 63 percent (60 to 81), IFS 9 km 72 percent (58 to 81).

GFS is different at the very top. Its heaviest 0.1 percent is not detectably lighter than the gauges' (minus 52 to plus 71 percent). It does produce totals that heavy. It just rarely puts them in the right hour and place: it caught 1.6 percent of the hours with 10 mm or more. At the heaviest 1 percent, every model is too light, GFS included, by 51 to 69 percent.

So the point-against-cell mismatch explains only a small part of the gap for heavy rain, which agrees with section 3. Most of it is the models.

## 8. Acted on, the forecasts keep little of what a perfect one would save

An error in millimetres does not say what a forecast is worth, so I scored a decision. Someone can protect against heavy rain at a cost, to avoid a bigger loss, and protects whenever the forecast says 10 mm or more. I compared what that costs them with the best fixed habit (always protect, or never) and with a perfect forecast. The share of the perfect forecast's saving they keep is the forecast's value.

For 6-hour totals one day ahead, GFS keeps at most 13 percent (5 to 18), when protecting costs about 5 percent of the loss it avoids. ECMWF keeps at most 6 percent (minus 4 to 10), not detectably above zero. Persistence, assuming tomorrow repeats today, keeps at most 9 percent (0 to 11). GFS has any value only when protecting costs between about 5 and 20 percent of the loss; outside that band, acting on it costs more than the best fixed habit. Hour by hour, with 10 mm in a single hour as the trigger, no forecast keeps more than 2 percent.

## 9. Judge the same forecasts by the reanalysis, and the verdict changes

ERA5 is the reanalysis most learned weather models are trained on and scored against. I added it two ways, both by root mean square error.

First, scored against the stations like any forecast. ERA5's temperature error is 9 percent larger than station climatology's (6 to 13), and it runs 0.6 degrees cool, even though observations went into it. Its wind error is about twice climatology's (88 to 106 percent larger), reading 1.4 metres per second too windy. For 6-hour rain it is not detectably different from climatology (minus 11 to plus 5 percent). Its heaviest 6-hour totals are 22 percent lighter than the gauges averaged over its cells (7 to 47): too light, but much less so than the forecasts.

Second, as the judge, on exactly the same station-hours, with an ERA5 climatology from the same years as the free guess. Of the 76 cells in the scorecard, 13 change colour. For temperature one day ahead, GFS's error is 3 percent lower than ECMWF's (0.3 to 7) against the instruments, and 38 percent higher (35 to 41) against ERA5: the two models swap places. ECMWF's AIFS, trained on ERA5 and then on ECMWF's own analyses, beats climatology in 12 of its 20 cells when ERA5 is the judge, against 7 when the instruments are. The 9 km IFS, the finest model here, looks worst for temperature when ERA5's 28 km cells are the judge.

ERA5 does what it is built to do: estimate the weather over a 28 km cell. A model trained and scored against it learns to match that cell, not the instruments inside it.

## 10. Most forecasts fail the standard benchmarks, and climatology passes

Regional modelling studies evaluate a simulation against stations with a fixed set of statistics and pass marks. The marks in common use (Emery and others, 2001) are, for temperature, a mean bias within 0.5 degrees and an index of agreement of at least 0.8; for wind, a bias within 0.5 metres per second, a root mean square error of at most 2 and an index of agreement of at least 0.6. I computed the same table, one day ahead, every station-hour pooled.

| | Temperature bias | RMSE | Agreement | Anomaly corr. | Wind bias | RMSE | Agreement | Anomaly corr. |
|---|---|---|---|---|---|---|---|---|
| GFS | -0.63 | 1.73 | 0.83 | 0.36 | 1.23 | 2.07 | 0.53 | 0.25 |
| ECMWF IFS 0.25 | -0.92 | 1.78 | 0.79 | 0.38 | 0.75 | 1.76 | 0.58 | 0.29 |
| ECMWF AIFS | -0.41 | 1.45 | 0.82 | 0.45 | 0.87 | 1.74 | 0.59 | 0.38 |
| ECMWF IFS 9 km | -1.04 | 1.89 | 0.80 | 0.37 | 0.41 | 1.45 | 0.65 | 0.32 |
| ERA5 | -0.63 | 1.66 | 0.77 | 0.40 | 1.42 | 2.21 | 0.55 | 0.38 |
| Persistence | 0.00 | 1.77 | 0.82 | 0.29 | 0.00 | 1.19 | 0.77 | 0.38 |
| Climatology | -0.31 | 1.52 | 0.82 | | 0.33 | 1.13 | 0.74 | |

Only AIFS passes for temperature and only the 9 km IFS for wind. Climatology and persistence pass both, with no model in them. In the tropics the daily cycle is most of the signal, so statistics that reward agreement with it cannot tell skill from routine. A pass on these marks says a forecast has the cycle right, not that it knows what is different about tomorrow.

The column that does separate them is the anomaly correlation: the correlation left after each station's climatology is subtracted from forecast and observation. It is positive for every forecast: 0.36 to 0.45 for temperature, 0.25 to 0.38 for wind, 0.17 to 0.35 for 6-hour rain. So the forecasts do follow the weather's departures from normal. The information is there. It is not expressed at the station.

## 11. Fitted to the stations, the same forecasts beat climatology

If the information is there, a model fitted to station data should recover it. I fitted the plainest one: a linear regression, per variable, on the station's climatology, the ECMWF and GFS one-day forecasts, the time of day and year, and the station's position. It was fitted on the test period up to 30 June 2025 and scored only on the 16 months after. The split date went into the config before the first fit, and nothing was tuned on the test months.

| Change in RMSE against climatology | Stations in training | Stations never seen |
|---|---|---|
| Temperature | -13% (-18 to -9) | -17% (-22 to -12), 19 stations |
| Wind | -13% (-15 to -10) | -16% (-21 to -11), 2 stations |
| Rain, 6-hour totals | -2% (-3 to -1) | -2% (-4 to -0.4), 26 stations |

On the same test days the raw forecasts were 12 to 17 percent worse than climatology for temperature and 58 to 92 percent worse for wind. The stations never seen joined the network after the training period ended, so the model had no history from them at all; it still gains there, which means it learned the forecast's errors and not the stations.

Gradient-boosted trees on the same inputs do no better: 10 percent for temperature, 16 percent for wind at trained stations but nothing detectable at new ones, and 4 percent worse than climatology for rain. With under three years at one site, there is nothing here for a deep network to add.

The rain gain is real and small, and section 3 says why: a model that only sees a 28 km grid cannot place rain inside it. What would help is what this model cannot take in and a larger one can: radar, satellite, and the stations around each station.

Sections 6 to 11 were added after the main scoring, and the protocol log says so. The scorecard and the extremes test follow published methods, the decision score is the standard cost-loss value, and the statistics in section 10 are the standard ones. The two percentiles and the five-gauge minimum were picked during a first look at the numbers, so treat them as a check rather than a test fixed in advance.

## What the case studies add

- **A monsoon surge in the wettest March on record, 2025.** Both models warned of it days ahead. The amount was another matter: 268 mm fell, GFS said 207, ECMWF said 121.
- **A squall line, 17 September 2024.** Thirty-one of 62 gauges took 10 mm or more in a single hour. No forecast had it, at any lead time.
- **An 18-day dry spell, July 2024.** 1.6 mm fell. GFS forecast 81 mm, with showers on most afternoons that never came.

The gauges alone found that dry spell on the same dates as the official record, to the day. That was my check that the observation side is right.

## What I am not claiming

A rain gauge is a point and a forecast is an average over a grid cell. Part of every low score is that mismatch. The test is under three years, so each monsoon season appears two or three times. The forecasts come from a public archive, and I have already found two faults in it. This is one region and one set of archives, not a ranking of models.

Every number here traces to a table in the repository. The rules were written down before the scoring, and everything added later is marked in the change log of [verification_protocol.md](verification_protocol.md).
