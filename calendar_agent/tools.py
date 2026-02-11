import sqlite3
import os
import json
from contextlib import nullcontext
from datetime import datetime
from zoneinfo import ZoneInfo
from datapizza.tools import tool
from opentelemetry import trace
from .utils import env_truthy

ROME_TZ = ZoneInfo("Europe/Rome")
DB_REVISION = 0
LIST_CACHE: dict[tuple[str, str, int], str] = {}
STRUCTURED = env_truthy("CALENDAR_STRUCTURED_OUTPUT", "0")

def _tracing_enabled() -> bool:
    return os.getenv("CALENDAR_TRACING", "").strip().lower() in {"1", "true"}

def _tool_cache_enabled() -> bool:
    return os.getenv("CALENDAR_TOOL_CACHE_ENABLED", "1").strip().lower() in {"1", "true"}

def _mark_cache_hit(layer: str) -> None:
    if not _tracing_enabled():
        return
    span = trace.get_current_span()
    if span is None:
        return
    span.set_attribute("cache.hit", True)
    span.set_attribute("cache.layer", layer)
    if hasattr(span, "add_event") and getattr(span, "is_recording", lambda: False)():
        span.add_event("cache.hit", {"cache.layer": layer})

def _span(name: str):
    if not _tracing_enabled():
        return nullcontext()
    tracer = trace.get_tracer(__name__)
    return tracer.start_as_current_span(name)

def _invalidate_tool_cache() -> None:
    global DB_REVISION, LIST_CACHE
    DB_REVISION += 1
    LIST_CACHE.clear()

def _get_db_path() -> str:
    return os.getenv("CALENDAR_DB_PATH", "./data/calendar.db")

def _connect() -> sqlite3.Connection:
    db_path = _get_db_path()
    os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def _parse_iso_rome(s: str) -> datetime:
    """
    Parses an ISO-8601 string. 
    If naive, assumes Europe/Rome. 
    If aware, converts to Europe/Rome.
    """
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=ROME_TZ)
    return dt.astimezone(ROME_TZ)

def _pretty_time(iso_str: str) -> str:
    """Formats an ISO string into a human-readable date/time."""
    dt = _parse_iso_rome(iso_str)
    return dt.strftime("%a %b %d, %H:%M")

def _event_row_to_dict(row: sqlite3.Row) -> dict:
    notes = row["notes"] if "notes" in row.keys() else None
    return {
        "id": int(row["id"]),
        "title": row["title"],
        "start": _parse_iso_rome(row["start_ts"]).isoformat(),
        "end": _parse_iso_rome(row["end_ts"]).isoformat(),
        "location": row["location"] if row["location"] else None,
        "notes": notes,
    }

def init_db() -> None:
    with _span("sqlite.init_db"):
        with _connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    start_ts TEXT NOT NULL,
                    end_ts TEXT NOT NULL,
                    location TEXT,
                    notes TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            # One-time cleanup: removed DELETE to persist data across sessions

def seed_db() -> None:
    with _connect() as conn:
        count = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
        if count == 0:
            now = datetime.now(ROME_TZ).isoformat()
            # Seeding with normalized Rome TZ timestamps
            conn.execute("""
                INSERT INTO events (title, start_ts, end_ts, location, notes, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, ("Project Kickoff", "2026-02-10T10:00:00+01:00", "2026-02-10T11:00:00+01:00", "Meeting Room A", "Discuss initial roadmap", now, now))

@tool
def list_events(start_iso: str, end_iso: str) -> str:
    """
    Lists calendar events within a specific ISO datetime range.
    
    Args:
        start_iso: Start of the range in ISO 8601 format.
        end_iso: End of the range in ISO 8601 format.
    """
    try:
        s_norm = _parse_iso_rome(start_iso).isoformat()
        e_norm = _parse_iso_rome(end_iso).isoformat()
    except ValueError:
        return "Error: Invalid ISO format for start or end time."

    cache_key = None
    if _tool_cache_enabled():
        cache_key = (s_norm, e_norm, DB_REVISION)
        cached = LIST_CACHE.get(cache_key)
        if cached is not None:
            _mark_cache_hit("tool")
            return cached

    with _span("sqlite.list_events") as span:
        if span is not None:
            span.set_attribute("query_range_start", s_norm)
            span.set_attribute("query_range_end", e_norm)

        with _connect() as conn:
            # Overlap logic: start_ts < end_iso AND end_ts > start_iso
            rows = conn.execute("""
                SELECT id, title, start_ts, end_ts, location, notes
                FROM events 
                WHERE start_ts < ? AND end_ts > ?
                ORDER BY start_ts ASC
            """, (e_norm, s_norm)).fetchall()

        if span is not None:
            span.set_attribute("rows_returned", len(rows))
        
        if STRUCTURED:
            result_obj = {
                "events": [_event_row_to_dict(r) for r in rows],
                "start": s_norm,
                "end": e_norm,
            }
            result = json.dumps(result_obj, separators=(",", ":"))
            if cache_key is not None:
                LIST_CACHE[cache_key] = result
            return result

        if not rows:
            result = "No events found in this range."
            if cache_key is not None:
                LIST_CACHE[cache_key] = result
            return result
            
        lines = []
        for r in rows:
            loc = f" @ {r['location']}" if r['location'] else ""
            start_p = _pretty_time(r['start_ts'])
            end_p = _parse_iso_rome(r['end_ts']).strftime("%H:%M")
            lines.append(f"[{r['id']}] {start_p}–{end_p} | {r['title']}{loc}")
        result = "\n".join(lines)
        if cache_key is not None:
            LIST_CACHE[cache_key] = result
        return result

@tool
def add_event(title: str, start_iso: str, end_iso: str, location: str = "", notes: str = "") -> str:
    """
    Adds a new event to the calendar.
    
    Args:
        title: Title of the event.
        start_iso: Start time in ISO 8601 format.
        end_iso: End time in ISO 8601 format.
        location: Optional location of the event.
        notes: Optional notes for the event.
    """
    try:
        dt_s = _parse_iso_rome(start_iso)
        dt_e = _parse_iso_rome(end_iso)
        if dt_s >= dt_e:
            return "Error: Start time must be before end time."
        
        start_iso_norm = dt_s.isoformat()
        end_iso_norm = dt_e.isoformat()
    except ValueError:
        return "Error: Invalid ISO format."

    now = datetime.now(ROME_TZ).isoformat()
    with _span("sqlite.add_event") as span:
        with _connect() as conn:
            cursor = conn.execute("""
                INSERT INTO events (title, start_ts, end_ts, location, notes, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (title, start_iso_norm, end_iso_norm, location, notes, now, now))
            event_id = cursor.lastrowid
            rows_affected = cursor.rowcount

        if span is not None:
            span.set_attribute("rows_affected", 1 if rows_affected == -1 else rows_affected)

        _invalidate_tool_cache()
        print(f"Created event {event_id} for {_pretty_time(start_iso_norm)}")
        if STRUCTURED:
            return json.dumps({"created_id": event_id}, separators=(",", ":"))
        return f"Event added successfully with ID: {event_id}"

@tool
def update_event(
    event_id: int, 
    title: str | None = None, 
    start_iso: str | None = None, 
    end_iso: str | None = None, 
    location: str | None = None, 
    notes: str | None = None
) -> str:
    """
    Updates an existing calendar event.
    
    Args:
        event_id: The ID of the event to update.
        title: New title.
        start_iso: New start time.
        end_iso: New end time.
        location: New location.
        notes: New notes.
    """
    fields = {k: v for k, v in {
        "title": title, "start_iso": start_iso, "end_iso": end_iso,
        "location": location, "notes": notes
    }.items() if v is not None}
    
    if not fields:
        return "Error: No fields provided for update."

    with _span("sqlite.update_event") as span:
        with _connect() as conn:
            event = conn.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()
            if not event:
                if span is not None:
                    span.set_attribute("rows_affected", 0)
                return f"Error: Event with ID {event_id} not found."
                
            new_start_iso = start_iso or event["start_ts"]
            new_end_iso = end_iso or event["end_ts"]
            
            try:
                dt_s = _parse_iso_rome(new_start_iso)
                dt_e = _parse_iso_rome(new_end_iso)
                if dt_s >= dt_e:
                    if span is not None:
                        span.set_attribute("rows_affected", 0)
                    return "Error: Updated start time must be before updated end time."
                
                # Update fields with normalized strings if they were provided
                if "start_iso" in fields: fields["start_iso"] = dt_s.isoformat()
                if "end_iso" in fields: fields["end_iso"] = dt_e.isoformat()
            except ValueError:
                if span is not None:
                    span.set_attribute("rows_affected", 0)
                return "Error: Invalid ISO format in update."

            update_sqls = []
            params = []
            for k, v in fields.items():
                col_name = k
                if k == "start_iso": col_name = "start_ts"
                if k == "end_iso": col_name = "end_ts"
                update_sqls.append(f"{col_name} = ?")
                params.append(v)
            
            params.append(datetime.now(ROME_TZ).isoformat())
            params.append(event_id)
            
            cursor = conn.execute(
                f"UPDATE events SET {', '.join(update_sqls)}, updated_at = ? WHERE id = ?",
                params
            )
            rows_affected = cursor.rowcount

        if span is not None:
            span.set_attribute("rows_affected", 0 if rows_affected == -1 else rows_affected)

        _invalidate_tool_cache()
        print(f"Edited event {event_id}")
        if STRUCTURED:
            return json.dumps({"updated_id": event_id}, separators=(",", ":"))
        return f"Event {event_id} updated successfully."

@tool
def delete_events(event_ids: list[int]) -> str:
    """
    Deletes one or more calendar events by their IDs.
    
    Args:
        event_ids: List of event IDs to delete.
    """
    if not event_ids:
        return "Error: No event IDs provided."
    if not all(isinstance(i, int) for i in event_ids):
        return "Error: All IDs must be integers."

    with _span("sqlite.delete_events") as span:
        with _connect() as conn:
            placeholders = ",".join("?" for _ in event_ids)
            cursor = conn.execute(f"DELETE FROM events WHERE id IN ({placeholders})", event_ids)
            rows_affected = cursor.rowcount

        if span is not None:
            span.set_attribute("rows_affected", 0 if rows_affected == -1 else rows_affected)
            span.set_attribute("event_ids_count", len(event_ids))

        _invalidate_tool_cache()
        print(f"Deleted event(s) {event_ids}")
        if STRUCTURED:
            return json.dumps(
                {"deleted_ids": list(event_ids), "deleted_count": rows_affected},
                separators=(",", ":"),
            )
        return f"Deleted {rows_affected} event(s). Attempted IDs: {event_ids}"

