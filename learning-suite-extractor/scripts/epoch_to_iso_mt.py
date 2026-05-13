#!/usr/bin/env python3
"""
Convert Unix epoch seconds to ISO 8601 strings with the correct Mountain Time
offset (MST -07:00 or MDT -06:00) for the given moment.

DST rules used:
- DST starts at 2:00 AM local time on the second Sunday of March.
- DST ends at 2:00 AM local time on the first Sunday of November.

Usage as a library:
    from epoch_to_iso_mt import epoch_to_iso_mt, datestr_to_iso_mt
    epoch_to_iso_mt(1736899140)
    datestr_to_iso_mt("2026-01-14 23:59:00")

Usage as a CLI:
    python3 epoch_to_iso_mt.py 1736899140
    python3 epoch_to_iso_mt.py "2026-01-14 23:59:00"
"""
from __future__ import annotations

import re
import sys
from datetime import datetime, timedelta, timezone

MST = timezone(timedelta(hours=-7), name="MST")
MDT = timezone(timedelta(hours=-6), name="MDT")


def _second_sunday_of_march(year: int) -> datetime:
    """Local-clock datetime when DST starts: 2:00 AM second Sunday of March."""
    d = datetime(year, 3, 1)
    # Find first Sunday
    while d.weekday() != 6:
        d += timedelta(days=1)
    # Add one week for the second Sunday
    d += timedelta(days=7)
    return d.replace(hour=2, minute=0, second=0)


def _first_sunday_of_november(year: int) -> datetime:
    """Local-clock datetime when DST ends: 2:00 AM first Sunday of November."""
    d = datetime(year, 11, 1)
    while d.weekday() != 6:
        d += timedelta(days=1)
    return d.replace(hour=2, minute=0, second=0)


def _mountain_tz_for_naive_local(local_naive: datetime) -> timezone:
    """Return MST or MDT for a given local-clock (naive) datetime."""
    year = local_naive.year
    dst_start = _second_sunday_of_march(year)
    dst_end = _first_sunday_of_november(year)
    return MDT if dst_start <= local_naive < dst_end else MST


def _mountain_tz_for_utc(utc_dt: datetime) -> timezone:
    """Return MST or MDT for a given UTC datetime by converting to local."""
    # MDT spans roughly 2nd Sun Mar 09:00 UTC through 1st Sun Nov 08:00 UTC.
    year = utc_dt.year
    dst_start_utc = _second_sunday_of_march(year).replace(tzinfo=MST).astimezone(timezone.utc)
    dst_end_utc = _first_sunday_of_november(year).replace(tzinfo=MDT).astimezone(timezone.utc)
    return MDT if dst_start_utc <= utc_dt < dst_end_utc else MST


def epoch_to_iso_mt(epoch_seconds: float | int | str | None) -> str | None:
    """Convert Unix epoch seconds to an ISO 8601 string with MT offset."""
    if epoch_seconds is None or epoch_seconds == "":
        return None
    epoch = float(epoch_seconds)
    utc_dt = datetime.fromtimestamp(epoch, tz=timezone.utc)
    tz = _mountain_tz_for_utc(utc_dt)
    return utc_dt.astimezone(tz).isoformat()


def datestr_to_iso_mt(s: str | None) -> str | None:
    """Convert a 'YYYY-MM-DD HH:MM:SS' (Mountain local, no offset) string to
    ISO 8601 with the correct MT offset attached."""
    if not s:
        return None
    if not isinstance(s, str):
        return str(s)
    s = s.strip()
    # Already has an offset? Return as-is.
    if re.search(r"[+-]\d\d:\d\d$", s) or s.endswith("Z"):
        return s
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            naive = datetime.strptime(s, fmt)
            tz = _mountain_tz_for_naive_local(naive)
            return naive.replace(tzinfo=tz).isoformat()
        except ValueError:
            continue
    # Unrecognized format; return untouched
    return s


def date_only(s: str | None) -> str | None:
    """Return just the YYYY-MM-DD prefix of a datetime string or ISO 8601."""
    if not s:
        return None
    return s.split("T")[0].split(" ")[0]


def _cli(argv: list[str]) -> int:
    if len(argv) < 2:
        print("Usage: epoch_to_iso_mt.py <epoch_seconds | 'YYYY-MM-DD HH:MM:SS'>")
        return 1
    val = argv[1]
    try:
        epoch = float(val)
        print(epoch_to_iso_mt(epoch))
    except ValueError:
        print(datestr_to_iso_mt(val))
    return 0


if __name__ == "__main__":
    sys.exit(_cli(sys.argv))
