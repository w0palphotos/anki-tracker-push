# Anki Tracker Push: Configuration

| Key | Purpose | Example |
|---|---|---|
| `apiUrl` | Full HTTPS URL of the tracker API endpoint | `https://your-domain.com/api/anki` |
| `token` | Shared secret sent as `Authorization: Bearer <token>` | `your-shared-secret` |
| `minSecondsBetweenPushes` | Throttle between live pushes (default: 15) | `15` |

Example `config.json`:

```json
{
  "apiUrl": "https://your-domain.com/api/anki",
  "token": "your-shared-secret",
  "minSecondsBetweenPushes": 15
}
```

The add-on also pushes on profile open, profile close, state changes, and after every sync, regardless of the throttle setting.
