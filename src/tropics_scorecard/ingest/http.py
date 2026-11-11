"""Cached HTTP GET with polite rate limiting and retries. Standard library only."""
from __future__ import annotations

import gzip
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

USER_AGENT = "tropics-scorecard/0.1 (open data research)"


class FetchError(RuntimeError):
    pass


class Throttle:
    """Keeps at least `interval` seconds between requests, and backs off on HTTP 429."""

    def __init__(self, interval: float):
        self.interval = interval
        self._last = 0.0

    def wait(self) -> None:
        delay = self._last + self.interval - time.monotonic()
        if delay > 0:
            time.sleep(delay)
        self._last = time.monotonic()


def get_bytes(url: str, throttle: Throttle | None = None, retries: int = 8, timeout: float = 120) -> bytes:
    backoff = 10.0
    for attempt in range(retries):
        if throttle:
            throttle.wait()
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read()
        except urllib.error.HTTPError as err:
            body = err.read()
            if err.code == 404:
                raise FetchError(f"404 {url}") from err
            if err.code in (429, 500, 502, 503, 504):
                print(f"retry after HTTP {err.code} in {backoff:.0f}s: {url}", file=sys.stderr, flush=True)
                time.sleep(backoff)
                backoff = min(backoff * 1.5, 120)
                continue
            raise FetchError(f"HTTP {err.code} {url}: {body[:200]!r}") from err
        except (urllib.error.URLError, TimeoutError, ConnectionError) as err:
            print(f"retry after {type(err).__name__} in {backoff:.0f}s: {url}", file=sys.stderr, flush=True)
            time.sleep(backoff)
            backoff = min(backoff * 1.5, 120)
    raise FetchError(f"gave up after {retries} attempts: {url}")


def cached_json(url: str, path: Path, throttle: Throttle | None = None) -> dict:
    """Return the JSON at `url`, reading `path` (gzip) if it exists, else fetching and saving it."""
    if path.exists():
        with gzip.open(path, "rt", encoding="utf-8") as fh:
            return json.load(fh)
    raw = get_bytes(url, throttle)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as err:
        raise FetchError(f"not JSON from {url}: {raw[:200]!r}") from err
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with gzip.open(tmp, "wb") as fh:
        fh.write(raw)
    tmp.replace(path)
    return data


def cached_file(url: str, path: Path, throttle: Throttle | None = None) -> Path:
    """Download `url` to `path` once."""
    if path.exists():
        return path
    raw = get_bytes(url, throttle)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(raw)
    tmp.replace(path)
    return path
