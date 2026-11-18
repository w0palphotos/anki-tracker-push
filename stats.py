"""Day bucketing for review timestamps. No Anki imports, so it is testable."""

import math
from datetime import datetime, timezone

MAX_DAYS = 371


def day_buckets(timestamps, day_start, days=MAX_DAYS):
    """Map review unix timestamps (seconds) to [["YYYY-MM-DD", count], ...].

    day_start is the unix time the current Anki day began
    (mw.col.sched.day_cutoff - 86400). Buckets run from that day backwards.
    """
    counts = {}
    for ts in timestamps:
        idx = int(math.floor((ts - day_start) / 86400.0))
        if -days < idx <= 0:
            counts[idx] = counts.get(idx, 0) + 1

    out = []
    for idx in range(0, -days, -1):
        stamp = day_start + idx * 86400
        out.append([datetime.fromtimestamp(stamp).strftime("%Y-%m-%d"), counts.get(idx, 0)])
    return out


def current_streak(days):
    """Consecutive non-zero days, allowing today to still be empty."""
    if not days:
        return 0
    start = 0 if days[0][1] else 1
    streak = 0
    for _, count in days[start:]:
        if count <= 0:
            break
        streak += 1
    return streak


def build_payload(timestamps, day_start, now=None):
    days = day_buckets(timestamps, day_start)
    now = now or datetime.now(timezone.utc)
    return {
        "v": 1,
        "days": days,
        "today": days[0][1],
        "totalReviews": sum(count for _, count in days),
        "currentStreak": current_streak(days),
        "updatedAt": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
