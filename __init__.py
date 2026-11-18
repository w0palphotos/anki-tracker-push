"""Anki add-on: push daily review counts to a public tracker endpoint.

Forked from Monacraft/AnkiDiscord; Discord/pypresence removed, Discord presence
replaced by an HTTP POST.
"""

from __future__ import annotations

import json
import threading
import time
import urllib.request

from aqt import mw

try:
    from aqt import gui_hooks
except ImportError:  # Anki older than 2.1.28
    gui_hooks = None

try:
    from .stats import MAX_DAYS, build_payload
except ImportError:
    from stats import MAX_DAYS, build_payload

DEFAULT_INTERVAL = 45

_push_lock = threading.Lock()
_last_push = 0.0
_pushing = False


def _config():
    return mw.addonManager.getConfig(__name__) or {}


def _collect():
    """Read revlog on the main thread; the HTTP POST runs in the worker."""
    col = mw.col
    if not col:
        return None
    cutoff = getattr(col.sched, "day_cutoff", None)
    if cutoff is None:
        cutoff = getattr(col.sched, "dayCutoff")
    day_start = int(cutoff) - 86400
    since_ms = (day_start - MAX_DAYS * 86400) * 1000
    rows = col.db.list("select id from revlog where id >= ?", since_ms) or []
    return build_payload([int(row) // 1000 for row in rows], day_start)


def _post(url, token, payload):
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer " + token,
        },
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        response.read()


def _run_push(url, token, payload):
    global _pushing
    try:
        _post(url, token, payload)
    except Exception as exc:
        print(f"[anki-tracker] push failed: {exc}")
    finally:
        with _push_lock:
            _pushing = False


def push(force=False):
    global _pushing, _last_push
    cfg = _config()
    url = (cfg.get("apiUrl") or "").strip()
    token = (cfg.get("token") or "").strip()
    if not url or not token:
        return

    interval = max(10, int(cfg.get("minSecondsBetweenPushes") or DEFAULT_INTERVAL))
    now = time.time()
    if not force and now - _last_push < interval:
        return
    with _push_lock:
        if _pushing:
            return
        _pushing = True

    try:
        payload = _collect()
    except Exception as exc:
        print(f"[anki-tracker] collection read failed: {exc}")
        with _push_lock:
            _pushing = False
        return

    _last_push = now
    if not payload:
        with _push_lock:
            _pushing = False
        return
    threading.Thread(target=_run_push, args=(url, token, payload), daemon=True).start()


def _on_answer(*_args):
    push()


def _on_profile_open():
    push(force=True)


def _on_profile_close():
    push(force=True)


def _on_sync_done(*_args):
    push(force=True)


if gui_hooks is not None and hasattr(gui_hooks, "reviewer_did_answer_card"):
    gui_hooks.reviewer_did_answer_card.append(_on_answer)
    gui_hooks.profile_did_open.append(_on_profile_open)
    gui_hooks.profile_will_close.append(_on_profile_close)
    if hasattr(gui_hooks, "sync_did_finish"):
        gui_hooks.sync_did_finish.append(_on_sync_done)
else:
    from anki.hooks import addHook

    addHook("showAnswer", _on_answer)
    addHook("profileLoaded", _on_profile_open)
    addHook("unloadProfile", _on_profile_close)
