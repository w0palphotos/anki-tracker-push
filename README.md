# Anki Tracker Push

An Anki add-on that pushes your daily review counts to a public tracker endpoint
(the Anki heatmap on a website) so the site updates without a manual export.

Forked from [Monacraft/AnkiDiscord](https://github.com/Monacraft/AnkiDiscord).
Discord Rich Presence and the vendored `pypresence` were removed; the presence
update is now a single HTTP POST.

## What it sends

```json
{
  "v": 1,
  "days": [["2026-11-18", 46], ["2026-11-17", 33]],
  "today": 46,
  "totalReviews": 3111,
  "currentStreak": 58,
  "updatedAt": "2026-11-18T12:00:00Z"
}
```

Only review counts per day, plus a timestamp. No card text, no deck names, no
account data. `days` covers the last 371 days.

## Install

1. Copy this folder into `Tools → Add-ons → View Files` (the `addons21` directory),
   or zip it and use *Install from file*.
2. Restart Anki.
3. `Tools → Add-ons → Anki Tracker Push → Config` and set `apiUrl` and `token`.
4. Review a card. A push goes out within `minSecondsBetweenPushes` seconds.

Pushes also fire on profile open, profile close, and after a sync.

## How days are bucketed

Anki's day boundary is `mw.col.sched.day_cutoff`, not midnight, so the add-on
buckets reviews by `day_cutoff - 86400 + n * 86400`. A review after the rollover
counts for the next day, exactly like Anki's own stats.

## Test

```sh
python3 tests/test_stats.py
```

Covers bucket boundaries, the 371-day window, empty buckets, and the streak rule
(today still empty does not reset yesterday's streak).
