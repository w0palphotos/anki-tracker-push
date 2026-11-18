"""Day bucketing and presence helpers for Anki Tracker Push."""

from __future__ import annotations

import math
from datetime import datetime, timezone

MAX_DAYS = 371


def day_buckets(timestamps, day_start, days=MAX_DAYS):
    """Map review unix timestamps (seconds) to [["YYYY-MM-DD", count], ...].

    day_start is unix timestamp of when current Anki day started (day_cutoff - 86400).
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


def build_payload(timestamps, day_start, presence=None, total_cards=None, now=None):
    days = day_buckets(timestamps, day_start)
    now = now or datetime.now(timezone.utc)
    data = {
        "v": 1,
        "days": days,
        "today": days[0][1],
        "totalReviews": sum(count for _, count in days),
        "currentStreak": current_streak(days),
        "updatedAt": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    if total_cards is not None:
        data["totalCards"] = total_cards
    if presence is not None:
        data["presence"] = presence
    return data
