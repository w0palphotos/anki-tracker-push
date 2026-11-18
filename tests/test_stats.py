import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from stats import current_streak, day_buckets  # noqa: E402

DAY = 86400
start = 1_700_000_000

# Today, yesterday, gap, three days ago
stamps = [start, start + 10, start + DAY - 1, start - DAY, start - 3 * DAY, start - 3 * DAY + 5]
days = day_buckets(stamps, start)
assert len(days) == 371, len(days)
assert days[0][1] == 3, days[0]
assert days[1][1] == 1, days[1]
assert days[2][1] == 0, days[2]
assert days[3][1] == 2, days[3]
assert days[0][0] != days[1][0]

# Day boundary: exactly at day_start is today, one second earlier is yesterday
edge = day_buckets([start, start - 1], start)
assert edge[0][1] == 1 and edge[1][1] == 1, edge[:2]

# Reviews older than the window are dropped
old = day_buckets([start - 500 * DAY], start, days=10)
assert sum(count for _, count in old) == 0

# Streak: a still-empty today does not reset yesterday's streak
assert current_streak([["d0", 0], ["d1", 2], ["d2", 1], ["d3", 0]]) == 2
assert current_streak([["d0", 1], ["d1", 0]]) == 1
assert current_streak([["d0", 0]]) == 0

print("ok")
