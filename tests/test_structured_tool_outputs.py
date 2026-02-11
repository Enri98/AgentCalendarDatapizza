import json
import os
import pytest

from calendar_agent import tools
from calendar_agent.utils import env_truthy


@pytest.fixture
def structured_tools(tmp_path, monkeypatch):
    db_file = tmp_path / "test_structured.db"
    original_structured = tools.STRUCTURED
    original_env = os.getenv("CALENDAR_STRUCTURED_OUTPUT")

    monkeypatch.setenv("CALENDAR_DB_PATH", str(db_file))
    monkeypatch.setenv("CALENDAR_STRUCTURED_OUTPUT", "1")
    tools.STRUCTURED = env_truthy("CALENDAR_STRUCTURED_OUTPUT", "0")
    tools.DB_REVISION = 0
    tools.LIST_CACHE.clear()
    tools.init_db()

    yield tools

    if original_env is None:
        monkeypatch.delenv("CALENDAR_STRUCTURED_OUTPUT", raising=False)
    else:
        monkeypatch.setenv("CALENDAR_STRUCTURED_OUTPUT", original_env)
    tools.STRUCTURED = original_structured


def test_structured_tool_outputs(structured_tools):
    add_payload = json.loads(
        structured_tools.add_event(
            "Structured Event",
            "2026-02-10T10:00:00",
            "2026-02-10T11:00:00",
            "Office",
            "Bring notes",
        )
    )
    assert "created_id" in add_payload
    event_id = add_payload["created_id"]

    list_payload = json.loads(
        structured_tools.list_events("2026-02-10T00:00:00", "2026-02-11T00:00:00")
    )
    assert set(list_payload.keys()) == {"events", "start", "end"}
    assert list_payload["events"]
    event = next(e for e in list_payload["events"] if e["id"] == event_id)
    assert set(event.keys()) == {"id", "title", "start", "end", "location", "notes"}
    assert event["location"] == "Office"
    assert event["notes"] == "Bring notes"
    assert event["start"].endswith("+01:00")
    assert event["end"].endswith("+01:00")

    update_payload = json.loads(
        structured_tools.update_event(event_id, title="Updated Structured Event")
    )
    assert update_payload == {"updated_id": event_id}

    delete_payload = json.loads(structured_tools.delete_events([event_id]))
    assert event_id in delete_payload["deleted_ids"]
    assert delete_payload["deleted_count"] == 1
