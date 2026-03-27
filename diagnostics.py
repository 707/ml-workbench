"""Lightweight in-app diagnostics log for deploy/runtime debugging."""

from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
import json


_EVENTS: deque[dict] = deque(maxlen=200)


def log_event(category: str, message: str, **fields) -> None:
    """Record a timestamped diagnostic event."""
    _EVENTS.append({
        "ts": datetime.now(timezone.utc).isoformat(),
        "category": category,
        "message": message,
        "fields": fields,
    })


def clear_events() -> None:
    """Clear the in-memory event buffer."""
    _EVENTS.clear()


def recent_events(limit: int = 25) -> list[dict]:
    """Return the most recent diagnostic events."""
    if limit <= 0:
        return []
    return list(_EVENTS)[-limit:]


def render_markdown(limit: int = 25) -> str:
    """Render recent diagnostics as markdown for Gradio."""
    events = recent_events(limit=limit)
    if not events:
        return "### Diagnostics\n- No recent events."

    lines = ["### Diagnostics"]
    for event in reversed(events):
        lines.append(
            f"- `{event['ts']}` [{event['category']}] {event['message']}"
        )
        fields = event.get("fields") or {}
        if fields:
            lines.append(f"  `{json.dumps(fields, ensure_ascii=True, sort_keys=True)}`")
    return "\n".join(lines)
