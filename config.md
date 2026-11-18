# Anki Tracker Push: Configuration

- **apiUrl**: full URL of the tracker endpoint, e.g. `https://your-domain.com/api/anki`.
- **token**: the secret token verified by the server. Sent in the request header as `Authorization: Bearer <token>`.
- **minSecondsBetweenPushes**: minimum gap between review pushes (default: 15). The add-on also pushes on state changes, profile open, profile close, and every 15 seconds during active sessions.
