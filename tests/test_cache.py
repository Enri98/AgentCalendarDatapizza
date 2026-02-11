import pytest
from calendar_agent import tools
from calendar_agent.cache import InMemoryLRUCache


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    db_file = tmp_path / "test_cache.db"
    monkeypatch.setenv("CALENDAR_DB_PATH", str(db_file))
    monkeypatch.setenv("CALENDAR_TOOL_CACHE_ENABLED", "1")
    tools.DB_REVISION = 0
    tools.LIST_CACHE.clear()
    tools.init_db()
    return db_file


def _seed_event():
    return tools.add_event(
        "Cached Event",
        "2026-02-10T10:00:00",
        "2026-02-10T11:00:00",
        "Home",
    )


def test_list_events_cache_hit(temp_db, monkeypatch):
    _seed_event()

    call_count = {"connect": 0}
    real_connect = tools._connect

    def counted_connect():
        call_count["connect"] += 1
        return real_connect()

    monkeypatch.setattr(tools, "_connect", counted_connect)

    res1 = tools.list_events("2026-02-10T00:00:00", "2026-02-11T00:00:00")
    res2 = tools.list_events("2026-02-10T00:00:00", "2026-02-11T00:00:00")

    assert "Cached Event" in res1
    assert res2 == res1
    assert call_count["connect"] == 1


def test_list_events_cache_invalidation_on_mutation(temp_db, monkeypatch):
    _seed_event()

    call_count = {"connect": 0}
    real_connect = tools._connect

    def counted_connect():
        call_count["connect"] += 1
        return real_connect()

    monkeypatch.setattr(tools, "_connect", counted_connect)

    tools.list_events("2026-02-10T00:00:00", "2026-02-11T00:00:00")
    assert call_count["connect"] == 1


def test_client_cache_records_saved_tokens(monkeypatch):
    class DummySpan:
        def __init__(self):
            self.attributes = {}
            self.events = []

        def set_attribute(self, key, value):
            self.attributes[key] = value

        def add_event(self, name, attributes=None):
            self.events.append((name, attributes or {}))

        def is_recording(self):
            return True

    class DummyUsage:
        prompt_tokens = 12
        completion_tokens = 3
        cached_tokens = 0

    class DummyResponse:
        usage = DummyUsage()

    span = DummySpan()
    monkeypatch.setenv("CALENDAR_TRACING", "1")
    monkeypatch.setattr("calendar_agent.cache.trace.get_current_span", lambda: span)

    cache = InMemoryLRUCache(maxsize=4)
    cache.set("k1", DummyResponse())

    cached = cache.get("k1")
    assert cached is not None

    cache_events = [e for e in span.events if e[0] == "cache.hit"]
    assert cache_events, "expected a cache.hit event"
    attrs = cache_events[-1][1]
    assert attrs["cache.layer"] == "client"
    assert attrs["cache.saved_prompt_tokens"] == 12
    assert attrs["cache.saved_completion_tokens"] == 3
    assert attrs["cache.saved_total_tokens"] == 15

    tools.add_event(
        "New Event",
        "2026-02-10T12:00:00",
        "2026-02-10T13:00:00",
        "Office",
    )

    call_count["connect"] = 0
    tools.list_events("2026-02-10T00:00:00", "2026-02-11T00:00:00")
    assert call_count["connect"] == 1
