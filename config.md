# Anki Tracker Push — config

- **apiUrl** — full URL of the tracker endpoint, e.g. `https://your-site.vercel.app/api/anki`.
- **token** — the `ANKI_TRACKER_TOKEN` value set on the server. Sent as `Authorization: Bearer …`.
- **minSecondsBetweenPushes** — minimum gap between pushes while reviewing. Push also runs on
  profile open, profile close, and after a sync.
