import os
import pytest
import sqlite3
from datetime import datetime
from zoneinfo import ZoneInfo
from calendar_agent.tools import init_db, list_events, add_event, update_event, delete_events
from calendar_agent.timeparse import resolve_range, resolve_event_start_end

@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    db_file = tmp_path / "test_calendar.db"
    monkeypatch.setenv("CALENDAR_DB_PATH", str(db_file))
    init_db()
    return db_file

def test_db_crud(temp_db):
    # Add
    res = add_event("Test Event", "2026-02-10T10:00:00", "2026-02-10T11:00:00", "Home")
    assert "ID: 1" in res
    
    # List (verify we find it even with offset normalized strings)
    events = list_events("2026-02-10T00:00:00", "2026-02-11T00:00:00")
    assert "Test Event" in events
    assert "Feb 10" in events # Asserting pretty date is present
    assert "[1]" in events
    
    # Update
    res = update_event(1, title="Updated Event")
    assert "success" in res.lower()
    events = list_events("2026-02-10T00:00:00", "2026-02-11T00:00:00")
    assert "Updated Event" in events

def test_time_parsing():
    now = datetime(2026, 2, 9, 10, 0, 0, tzinfo=ZoneInfo("Europe/Rome"))
    
    # resolve_range
    r = resolve_range("tomorrow morning", now)
    assert "+01:00" in r[0] # Offset included
    assert "08:00:00" in r[0]
    
    # resolve_event_start_end
    e = resolve_event_start_end("tomorrow at 10", now)
    assert "10:00:00+01:00" in e[0]
    
    # Test "no day keyword" rule
    assert resolve_event_start_end("at 10", now) is None

