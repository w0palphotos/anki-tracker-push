# Web Integration Guide

How the tracker API and the portfolio frontend fit together, and how to reuse
the pieces — including the Discord-style presence card — in your own site.

## Architecture

```
┌─────────────┐  POST /api/anki   ┌──────────────────┐       ┌─────────────┐
│ Anki add-on │ ────────────────► │  Tracker API     │ ────► │ Upstash     │
│ (this repo) │  Bearer token     │  (Vercel fn)     │       │ Redis       │
└─────────────┘                   └──────────────────┘       └─────────────┘
                                       ▲        │
                          GET /api/anki│        │ GET (poll, 3s)
                                       │        ▼
                                  ┌──────────────────┐
                                  │  Portfolio web   │
                                  │  heatmap + card  │
                                  └──────────────────┘
```

The add-on **pushes**; the website **polls**. The lab/device running Anki never
needs to be reachable from the internet — it only makes outbound HTTPS calls.

## Tracker API reference (`api/anki.js`)

A single Vercel serverless function (also runnable locally, see below).

### `GET /api/anki`

Returns the last pushed state:

```json
{
  "days": [["2026-11-19", 1], ["2026-11-18", 56]],
  "today": 1,
  "totalReviews": 3122,
  "totalCards": 1501,
  "currentStreak": 44,
  "updatedAt": "2026-11-19T15:37:03.000Z",
  "presence": { "status": "offline", "updatedAt": "2026-11-19T15:37:03.000Z" },
  "storage": "redis"
}
```

- `404` until the first push arrives.
- **Presence freshness:** the API flips `presence.status` to `offline` when the
  add-on reported offline OR the last presence heartbeat is older than **45 s**
  (the add-on heartbeats every 15 s, so 45 s tolerates two missed beats).
- `days` is newest-first, up to 371 entries, aligned to Anki's `day_cutoff`.
- Responses are edge-cacheable (`Cache-Control: public, s-maxage=5,
  stale-while-revalidate=30`) so traffic spikes don't multiply Redis load.

### `POST /api/anki`

- Auth: `Authorization: Bearer <ANKI_TRACKER_TOKEN>` (required when the env var
  is set).
- Body: `v: 1` payload (see the README for full and offline-ping shapes).
- Offline pings and partial updates **preserve stored review history** — they
  only touch presence.
- The server stamps `presence.updatedAt` and recomputes totals/streak fallbacks.
- Storage: Upstash Redis when `UPSTASH_REDIS_REST_URL` + `UPSTASH_REDIS_REST_TOKEN`
  are set (key `anki:stats`); otherwise in-memory (lost on cold start).

### Server env vars

| Var | Purpose |
|---|---|
| `ANKI_TRACKER_TOKEN` | Shared secret the add-on sends |
| `UPSTASH_REDIS_REST_URL` | Redis REST endpoint (persistence) |
| `UPSTASH_REDIS_REST_TOKEN` | Redis REST token |

## Frontend integration

The reference implementation lives in `portfolio-web` (Vue 3 + Vite). Three
pieces:

### 1. Shared polling composable

One poll loop shared by every component that needs Anki data (module-level
singleton with subscriber counting — components mounting/unmounting don't
multiply requests):

```ts
// useAnkiStats.ts (simplified)
const stats = ref<AnkiStatsData | null>(null)
let subscribers = 0
let timer: ReturnType<typeof setInterval> | null = null

async function load() {
  const res = await fetch(import.meta.env.VITE_ANKI_API || '/api/anki', { cache: 'no-store' })
  if (res.ok) {
    const data = await res.json()
    if (Array.isArray(data.days)) stats.value = data
  }
}

export function useAnkiStats() {
  onMounted(() => {
    if (++subscribers === 1) {
      load()
      timer = setInterval(load, 3000)
    }
  })
  onUnmounted(() => {
    if (--subscribers === 0 && timer) { clearInterval(timer); timer = null }
  })
  return { stats }
}
```

### 2. Review heatmap (`AnkiStats.vue`)

GitHub-style contribution graph built from `days`:

- Desktop: 53 weeks (a year).
- Mobile (`max-width: 767px`): starts at the **first day with reviews** instead
  of a year of empty cells — much better signal on small screens.
- Summary line: total cards · streak · reviews today. Streak falls back to
  counting consecutive active days when the pushed streak is 0.

### 3. Persistent presence card (`AnkiDiscordCard.vue`)

A Discord-style "PLAYING A GAME" activity card. **It stays mounted when Anki
is closed** — it just switches to an idle rendering:

| `presence.status` | Rendering |
|---|---|
| `online` | "PLAYING A GAME" header, state + details lines, live elapsed timer, activity badge (💤 / 🔍 / ✓ / ⋯) |
| `offline` | "OFFLINE" header, dimmed logo, grey dot badge, "Not studying right now", no activity, no timer |

Usage in a page:

```vue
<script setup lang="ts">
import { useAnkiStats } from '@/composables/useAnkiStats'
import AnkiDiscordCard from '@/components/AnkiDiscordCard.vue'
const { stats } = useAnkiStats()
</script>

<template>
  <!-- Persistent: render whenever presence exists, online OR offline -->
  <AnkiDiscordCard v-if="stats?.presence" :presence="stats.presence" />
  <div v-else>Waiting for Anki sync…</div>
</template>
```

## Reusing the card in another project

A ready-to-copy component ships in this repo:
[`docs/AnkiDiscordCard.vue`](AnkiDiscordCard.vue).

- **Plain Vue 3 SFC** (`<script setup lang="ts">`), no dependencies beyond Vue.
  Scoped CSS, Discord-dark palette hardcoded — works on any background.
- Drop it into your components directory and pass a `presence` prop:

```ts
interface Presence {
  status: 'online' | 'offline'
  state?: string      // e.g. "Daily reviews"
  details?: string    // e.g. "68 cards left (56 done today)"
  startedAt?: number  // unix SECONDS — drives the elapsed timer
  icon?: string       // 'zzz' | 'search' | 'tick-dark' | 'ellipsis-dark' | …
}
```

- Feed it from any backend that speaks the payload format — poll `GET
  /api/anki` every few seconds, or adapt the props to your own presence source
  (the component only cares about the shape above).
- The elapsed timer ticks locally every second from `startedAt`, so it stays
  smooth between polls.
- Not using Vue? The markup/CSS is small and self-contained — port the template
  and styles to your framework of choice; the only logic is the elapsed-time
  formatter.

## Local development

`portfolio-web` ships a dev server that runs the same Vercel-style handlers
locally:

```sh
npm run dev:api   # node --env-file=.env scripts/dev-api.mjs → :3001
npm run dev       # vite → :5173, proxies /api/* to :3001
```

Point the add-on config at `http://<your-lan-ip>:3001/api/anki` while testing
(Anki must be able to reach that address), or at your deployed URL.

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| Card stuck "Waiting for Anki sync" | No push arrived yet — check add-on config (`apiUrl`, `token`) and Anki's console for `[anki-tracker]` lines |
| Card flips offline while Anki is open | Heartbeats blocked (network/proxy) — pushes fire every 15 s; API marks stale after 45 s |
| Heatmap resets after closing Anki | API running in-memory mode — configure Upstash env vars |
| `401 unauthorized` on push | Add-on `token` ≠ server `ANKI_TRACKER_TOKEN` |
| Streak shows 0 with active days | Today at 0 doesn't break the streak; the frontend also recomputes from `days` as a fallback |
