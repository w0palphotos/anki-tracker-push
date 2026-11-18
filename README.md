# Anki Tracker Push

An Anki add-on that pushes your daily review counts and live study presence to a tracker endpoint (such as a personal website or portfolio).

Forked from [Monacraft/AnkiDiscord](https://github.com/Monacraft/AnkiDiscord). Discord client RPC (`pypresence`) was replaced with direct HTTP POST updates, allowing any web frontend to show live Discord-style activity cards and GitHub-style heatmaps without running Discord on the desktop.

## What it sends

### Live update payload

```json
{
  "v": 1,
  "days": [["2026-11-18", 56], ["2026-11-17", 33]],
  "today": 56,
  "totalReviews": 3121,
  "totalCards": 1501,
  "currentStreak": 43,
  "updatedAt": "2026-11-18T18:58:36Z",
  "presence": {
    "status": "online",
    "state": "Daily reviews",
    "details": "68 cards left (56 done today)",
    "startedAt": 1795027639,
    "icon": "tick-dark"
  }
}
```

### Shutdown payload

When Anki closes, the add-on sends a lightweight presence update so the web card updates to offline immediately without touching stored review history:

```json
{
  "v": 1,
  "presence": {
    "status": "offline"
  }
}
```

## Features

- **Live presence**: reports current app state (reviewing, browsing decks, editing, menus), cards left, cards reviewed today, and start timestamp.
- **Accurate counts**: reads the root deck node directly to avoid double-counting due cards across nested decks.
- **Real-time push**: triggers on card answers, navigation changes, profile syncs, and a 15-second background heartbeat loop.
- **Review heatmap**: aggregates review timestamps over the last 371 days into daily buckets matching Anki's custom rollover cutoff (`day_cutoff`).
- **Streak calculation**: counts continuous active days, allowing the current day to start at 0 without breaking the streak.
- **Total card inventory**: sends total cards owned in collection alongside review history.

## Installation

1. Copy this folder into your Anki add-on directory (`Tools -> Add-ons -> View Files`), or install the `.ankiaddon` package via `Tools -> Add-ons -> Install from file...`.
2. Restart Anki.
3. Open `Tools -> Add-ons -> Anki Tracker Push -> Config` and set your `apiUrl` and `token`.
4. Start reviewing. Updates post automatically.

## Configuration

In `config.json`:

```json
{
  "apiUrl": "https://your-domain.com/api/anki",
  "token": "your-secret-token",
  "minSecondsBetweenPushes": 15
}
```

- `apiUrl`: full HTTPS endpoint for your tracker API (e.g. Vercel serverless function).
- `token`: bearer token verified by your API endpoint via `Authorization: Bearer <token>`.
- `minSecondsBetweenPushes`: minimum throttle interval for live pushes (default: 15 seconds).

## Testing

Run unit tests for bucketing and streak calculation:

```sh
python3 tests/test_stats.py
```
