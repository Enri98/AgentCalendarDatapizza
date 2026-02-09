import sqlite3
import os
from datetime import datetime
from datapizza.tools import tool

def _get_db_path() -> str:
    return os.getenv("CALENDAR_DB_PATH", "./data/calendar.db")

def _connect() -> sqlite3.Connection:
    db_path = _get_db_path()
    os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def init_db() -> None:
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

def seed_db() -> None:
    with _connect() as conn:
        count = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
        if count == 0:
            now = datetime.now().isoformat()
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
        datetime.fromisoformat(start_iso)
        datetime.fromisoformat(end_iso)
    except ValueError:
        return "Error: Invalid ISO format for start or end time."

    with _connect() as conn:
        # Overlap logic: start_ts < end_iso AND end_ts > start_iso
        rows = conn.execute("""
            SELECT id, title, start_ts, end_ts, location 
            FROM events 
            WHERE start_ts < ? AND end_ts > ?
            ORDER BY start_ts ASC
        """, (end_iso, start_iso)).fetchall()
        
        if not rows:
            return "No events found in this range."
            
        lines = []
        for r in rows:
            loc = f" @ {r['location']}" if r['location'] else ""
            lines.append(f"[{r['id']}] {r['start_ts']}–{r['end_ts']} | {r['title']}{loc}")
        return "\n".join(lines)

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
        s = datetime.fromisoformat(start_iso)
        e = datetime.fromisoformat(end_iso)
        if s >= e:
            return "Error: Start time must be before end time."
    except ValueError:
        return "Error: Invalid ISO format."

    now = datetime.now().isoformat()
    with _connect() as conn:
        cursor = conn.execute("""
            INSERT INTO events (title, start_ts, end_ts, location, notes, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (title, start_iso, end_iso, location, notes, now, now))
        return f"Event added successfully with ID: {cursor.lastrowid}"

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

    with _connect() as conn:
        event = conn.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()
        if not event:
            return f"Error: Event with ID {event_id} not found."
            
        new_start = start_iso or event["start_ts"]
        new_end = end_iso or event["end_ts"]
        if datetime.fromisoformat(new_start) >= datetime.fromisoformat(new_end):
            return "Error: Updated start time must be before updated end time."

        update_sqls = []
        params = []
        for k, v in fields.items():
            if k == "start_iso": k = "start_ts"
            if k == "end_iso": k = "end_ts"
            update_sqls.append(f"{k} = ?")
            params.append(v)
        
        params.append(datetime.now().isoformat())
        params.append(event_id)
        
        conn.execute(f"UPDATE events SET {', '.join(update_sqls)}, updated_at = ? WHERE id = ?", params)
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

    with _connect() as conn:
        placeholders = ",".join("?" for _ in event_ids)
        cursor = conn.execute(f"DELETE FROM events WHERE id IN ({placeholders})", event_ids)
        return f"Deleted {cursor.rowcount} event(s). Attempted IDs: {event_ids}"

