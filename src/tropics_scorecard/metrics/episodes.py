"""Merge intervals into episodes."""


def merge_intervals(intervals, max_gap=0):
    """Merge intervals that overlap or lie within max_gap of each other.

    intervals: iterable of (start, end) with start <= end, in any order.
    Two intervals merge when next.start <= current.end + max_gap.
    Returns a list of (start, end) tuples sorted by start. The input is not
    modified. ValueError when an interval has start > end.
    """
    out = []
    for start, end in sorted(intervals):
        if start > end:
            raise ValueError(f"interval ({start}, {end}) has start after end")
        if out and start <= out[-1][1] + max_gap:
            out[-1] = (out[-1][0], max(out[-1][1], end))
        else:
            out.append((start, end))
    return out
