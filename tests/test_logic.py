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
    res = add_event("Test Event", "2026-02-10T10:00:00+01:00", "2026-02-10T11:00:00+01:00", "Home")
    assert "ID: 1" in res
    
    # List
    events = list_events("2026-02-10T00:00:00+01:00", "2026-02-11T00:00:00+01:00")
    assert "Test Event" in events
    assert "[1]" in events
    
    # Update
    res = update_event(1, title="Updated Event")
    assert "success" in res.lower()
    events = list_events("2026-02-10T00:00:00+01:00", "2026-02-11T00:00:00+01:00")
    assert "Updated Event" in events
    
    # Delete
    res = delete_events([1])
    assert "Deleted 1" in res
    events = list_events("2026-02-10T00:00:00+01:00", "2026-02-11T00:00:00+01:00")
    assert "No events found" in events

def test_time_parsing():
    now = datetime(2026, 2, 9, 10, 0, 0, tzinfo=ZoneInfo("Europe/Rome"))
    
    # resolve_range
    r = resolve_range("tomorrow morning", now)
    assert r[0].startswith("2026-02-10T08:00:00")
    assert r[1].startswith("2026-02-10T12:00:00")
    
    r = resolve_range("today", now)
    assert r[0].startswith("2026-02-09T00:00:00")
    
    # resolve_event_start_end
    e = resolve_event_start_end("tomorrow at 10", now)
    assert e[0].startswith("2026-02-10T10:00:00")
    assert e[1].startswith("2026-02-10T11:00:00") # default 60m
    
    e = resolve_event_start_end("14-16 today", now)
    assert e[0].startswith("2026-02-09T14:00:00")
    assert e[1].startswith("2026-02-09T16:00:00")
