"""Rebuild everything from the cached downloads, in order, with one command.

    python -m tropics_scorecard.pipeline build     # tables, quality control, reference, dashboard data
    python -m tropics_scorecard.pipeline score     # every score (needs the protocol signed off)
    python -m tropics_scorecard.pipeline all       # both

Downloads are separate (ingest.datagovsg, ingest.isd, ingest.igra, ingest.openmeteo, ingest.era5): this
command never touches the network, so it is safe to rerun at any time.
"""
from __future__ import annotations

import argparse
import sys
import time

from .paths import TABLES, load_config

DGS_VARIABLES = ("rainfall", "air-temperature", "wind-speed")
YEARS = range(2017, 2027)


def _step(name: str):
    print(f"\n== {name}", flush=True)
    return time.monotonic()


def _done(t0: float) -> None:
    print(f"   {time.monotonic() - t0:.0f}s", flush=True)


def build(cfg: dict) -> None:
    from . import export
    from .cases import replay
    from .match import observations
    from .qc import run as qc
    from .store import datagovsg, openmeteo

    t = _step("station readings")
    for v in DGS_VARIABLES:
        for y in YEARS:
            p = datagovsg.build(v, y)
            if p:
                print(f"   {v} {y}", flush=True)
    _done(t)

    t = _step("quality control")
    for v in DGS_VARIABLES:
        for y in YEARS:
            if (TABLES / "datagovsg" / f"readings_{v}_{y}.parquet").exists():
                r = qc.run_datagovsg(cfg, v, y)
                print(f"   {v} {y}: {int(r['summary']['flags'].sum()) if len(r['summary']) else 0} flags", flush=True)
    qc.run_isd(cfg)
    _done(t)

    t = _step("hourly reference")
    for v in observations.VARIABLES:
        for y in YEARS:
            observations.build(v, y, cfg)
    _done(t)

    t = _step("forecast tables")
    openmeteo.main([])
    _done(t)

    t = _step("ERA5 table")
    from .ingest.era5 import FOLDER
    from .sources import era5

    if (FOLDER / "cells").exists():
        era5.store()
    _done(t)

    t = _step("dashboard data and case replays")
    export.main([])
    replay.main(["--all"])
    _done(t)


def score(cfg: dict) -> None:
    from . import export
    from .scorer import core, reanalysis, summary

    t = _step("scoring")
    df = core.run_all(cfg)
    print(f"   {core.summary_numbers(df)}", flush=True)
    _done(t)

    t = _step("scorecard, extremes and decision tables")
    summary.main(cfg)
    _done(t)

    t = _step("ERA5: scored against the stations, and as a second judge")
    reanalysis.main(cfg)
    _done(t)
    export.main([])


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("step", choices=["build", "score", "all"])
    args = ap.parse_args(argv)
    cfg = load_config()
    if args.step in ("build", "all"):
        build(cfg)
    if args.step in ("score", "all"):
        score(cfg)
    return 0


if __name__ == "__main__":
    sys.exit(main())
