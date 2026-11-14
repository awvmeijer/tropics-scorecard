"""Always dry: a rain forecast of zero for every hour.

Not a forecast anyone would use. It is here because it exposes a score: over rain, which is
zero most of the time, mean absolute error is lowest for a forecast that never rains. A
score this baseline wins cannot be the headline for rain.
"""
from __future__ import annotations

import pandas as pd

from ..sources import ForecastSource, check_cases


class AlwaysDry(ForecastSource):
    name = "always_dry"

    def predict(self, variable: str, cases: pd.DataFrame) -> pd.Series:
        check_cases(cases)
        if variable != "rain_hourly":
            return pd.Series(float("nan"), index=cases.index)
        return pd.Series(0.0, index=cases.index)
