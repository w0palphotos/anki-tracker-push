"""Anki add-on: push daily review counts and live activity presence to tracker endpoint in realtime."""

from __future__ import annotations

import json
import threading
import time
import urllib.request
from datetime import datetime, timezone

from aqt import mw

try:
    from aqt import gui_hooks
except ImportError:
    gui_hooks = None

try:
    from .stats import MAX_DAYS, build_payload
except ImportError:
    from stats import MAX_DAYS, build_payload

_push_lock = threading.Lock()
_last_push = 0.0
_pushing = False
_app_start_time = int(time.time())
_current_state = "deckBrowser"
_heartbeat_thread = None


def _config():
    return mw.addonManager.getConfig(__name__) or {}


def _get_due_and_done():
    """Calculate due count and cards done today accurately across Anki versions."""
    col = mw.col
    if not col:
        return 0, 0

    # 1. Cards done today
    try:
        cutoff = getattr(col.sched, "day_cutoff", None)
        if cutoff is None:
            cutoff = getattr(col.sched, "dayCutoff")
        anki_today_start = int((int(cutoff) - 86400) * 1000)
        reviews_today = col.db.scalar(
            "SELECT count(*) FROM revlog WHERE id > ?", anki_today_start
        ) or 0
    except Exception:
        reviews_today = 0

    # 2. Due cards
    due_count = 0
    try:
        if hasattr(col.sched, "deck_due_tree"):
            tree = col.sched.deck_due_tree()
            if tree:
                # In modern Anki, the root node's review_count, learn_count, and new_count
                # ALREADY include all children deck counts after applying deck limits!
                # If deck_id == 0, it is the root of the whole tree.
                if getattr(tree, "deck_id", None) == 0:
                    due_count = (
                        getattr(tree, "review_count", 0)
                        + getattr(tree, "learn_count", 0)
                        + getattr(tree, "new_count", 0)
                    )
                else:
                    # If root has children at top-level, sum only the top-level direct children
                    for child in getattr(tree, "children", []):
                        due_count += (
                            getattr(child, "review_count", 0)
                            + getattr(child, "learn_count", 0)
                            + getattr(child, "new_count", 0)
                        )
        elif hasattr(col.sched, "deckDueTree"):
            for deck_info in col.sched.deckDueTree():
                due_count += deck_info[2] + deck_info[3] + deck_info[4]
    except Exception:
        pass

    return due_count, reviews_today


def _get_presence(status="online"):
    if status == "offline":
        return {"status": "offline"}

    col = mw.col
    if not col:
        return {
            "status": "online",
            "state": "Chilling in the menus",
            "details": "Starting up...",
            "startedAt": _app_start_time,
            "icon": "zzz",
        }

    due, done = _get_due_and_done()

    if _current_state == "review":
        state_text = "Daily reviews"
        icon = "tick-dark"
    elif _current_state == "browse":
        state_text = "Browsing decks"
        icon = "search"
    elif _current_state == "edit":
        state_text = "Adding cards"
        icon = "ellipsis-dark"
    else:
        state_text = "Chilling in the menus"
        icon = "zzz"

    if due == 0:
        details = f"Done for today! ({done} cards completed)"
    elif due == 1:
        details = f"1 card left ({done} done today)"
    else:
        details = f"{due} cards left ({done} done today)"

    return {
        "status": "online",
        "state": state_text,
        "details": details,
        "startedAt": _app_start_time,
        "icon": icon,
    }


def _collect(status="online"):
    col = mw.col
    presence = _get_presence(status)
    if not col:
        now = datetime.now(timezone.utc)
        return {
            "v": 1,
            "days": [],
            "today": 0,
            "totalReviews": 0,
            "currentStreak": 0,
            "updatedAt": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "presence": presence,
        }

    cutoff = getattr(col.sched, "day_cutoff", None)
    if cutoff is None:
        cutoff = getattr(col.sched, "dayCutoff")
    day_start = int(cutoff) - 86400
    since_ms = (day_start - MAX_DAYS * 86400) * 1000
    rows = col.db.list("select id from revlog where id >= ?", since_ms) or []

    # Get total cards in collection
    total_cards = None
    try:
        total_cards = col.db.scalar("select count(*) from cards")
    except Exception:
        pass

    return build_payload(
        [int(row) // 1000 for row in rows],
        day_start,
        presence=presence,
        total_cards=total_cards,
    )


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
    with urllib.request.urlopen(request, timeout=5) as response:
        response.read()


def _run_push(url, token, payload):
    global _pushing
    try:
        _post(url, token, payload)
        state_desc = payload.get("presence", {}).get("state", "sync")
        details = payload.get("presence", {}).get("details", "")
        print(f"[anki-tracker] Realtime push success: {state_desc} - {details} (today: {payload.get('today', 0)}, streak: {payload.get('currentStreak', 0)})")
    except Exception as exc:
        print(f"[anki-tracker] Realtime push failed: {exc}")
    finally:
        with _push_lock:
            _pushing = False


def push(force=False, status="online"):
    global _pushing, _last_push
    cfg = _config()
    url = (cfg.get("apiUrl") or "").strip()
    token = (cfg.get("token") or "").strip()
    if not url or not token:
        print("[anki-tracker] Not configured: apiUrl or token missing in Tools -> Add-ons -> Config")
        return

    now = time.time()
    if not force and (now - _last_push) < 2:
        return

    with _push_lock:
        if _pushing and not force:
            return
        _pushing = True

    try:
        payload = _collect(status=status)
    except Exception as exc:
        print(f"[anki-tracker] collection read error: {exc}")
        with _push_lock:
            _pushing = False
        return

    _last_push = now
    if not payload:
        with _push_lock:
            _pushing = False
        return

    if force and status == "offline":
        try:
            _post(url, token, payload)
            print("[anki-tracker] Sent offline signal successfully")
        except Exception:
            pass
        finally:
            with _push_lock:
                _pushing = False
    else:
        threading.Thread(target=_run_push, args=(url, token, payload), daemon=True).start()


def _heartbeat_loop():
    """Background heartbeat loop every 15s so web presence stays alive."""
    while True:
        time.sleep(15)
        try:
            push(force=True, status="online")
        except Exception:
            pass


def _on_state_change(new_state, old_state=None):
    global _current_state
    _current_state = new_state
    push(force=True, status="online")


def _on_answer(*_args):
    push(force=True, status="online")


def _on_profile_open():
    global _heartbeat_thread
    push(force=True, status="online")
    if _heartbeat_thread is None:
        _heartbeat_thread = threading.Thread(target=_heartbeat_loop, daemon=True)
        _heartbeat_thread.start()


def _on_profile_close():
    push(force=True, status="offline")


def _on_sync_done(*_args):
    push(force=True, status="online")


if gui_hooks is not None:
    if hasattr(gui_hooks, "state_did_change"):
        gui_hooks.state_did_change.append(_on_state_change)
    if hasattr(gui_hooks, "reviewer_did_answer_card"):
        gui_hooks.reviewer_did_answer_card.append(_on_answer)
    if hasattr(gui_hooks, "profile_did_open"):
        gui_hooks.profile_did_open.append(_on_profile_open)
    if hasattr(gui_hooks, "profile_will_close"):
        gui_hooks.profile_will_close.append(_on_profile_close)
    if hasattr(gui_hooks, "sync_did_finish"):
        gui_hooks.sync_did_finish.append(_on_sync_done)
    if hasattr(gui_hooks, "main_window_did_init"):
        gui_hooks.main_window_did_init.append(lambda: push(force=True, status="online"))
else:
    from anki.hooks import addHook
    addHook("afterStateChange", _on_state_change)
    addHook("showAnswer", _on_answer)
    addHook("profileLoaded", _on_profile_open)
    addHook("unloadProfile", _on_profile_close)

import atexit
atexit.register(lambda: push(force=True, status="offline"))
