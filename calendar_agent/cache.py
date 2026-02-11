import os
from collections import OrderedDict
from typing import Any

from datapizza.core.cache import Cache
from opentelemetry import trace


def _env_enabled(name: str, default: str = "1") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true"}


def _mark_cache_hit(layer: str) -> None:
    if not _env_enabled("CALENDAR_TRACING", "0"):
        return
    span = trace.get_current_span()
    if span is None:
        return
    span.set_attribute("cache.hit", True)
    span.set_attribute("cache.layer", layer)
    if hasattr(span, "add_event") and getattr(span, "is_recording", lambda: False)():
        span.add_event("cache.hit", {"cache.layer": layer})


def _record_cache_savings(layer: str, value: Any) -> None:
    if not _env_enabled("CALENDAR_TRACING", "0"):
        return
    span = trace.get_current_span()
    if span is None or not getattr(span, "is_recording", lambda: False)():
        return
    usage = getattr(value, "usage", None)
    if usage is None:
        return
    prompt_tokens = int(getattr(usage, "prompt_tokens", 0) or 0)
    completion_tokens = int(getattr(usage, "completion_tokens", 0) or 0)
    cached_tokens = int(getattr(usage, "cached_tokens", 0) or 0)
    total_tokens = prompt_tokens + completion_tokens + cached_tokens
    span.add_event(
        "cache.hit",
        {
            "cache.layer": layer,
            "cache.saved_prompt_tokens": prompt_tokens,
            "cache.saved_completion_tokens": completion_tokens,
            "cache.saved_cached_tokens": cached_tokens,
            "cache.saved_total_tokens": total_tokens,
        },
    )


class InMemoryLRUCache(Cache):
    def __init__(self, maxsize: int = 128):
        self.maxsize = maxsize
        self._enabled = _env_enabled("CALENDAR_CLIENT_CACHE_ENABLED", "1")
        self._cache: OrderedDict[str, Any] = OrderedDict()

    def get(self, key: str) -> Any | None:
        if not self._enabled:
            return None
        if key not in self._cache:
            return None
        value = self._cache.pop(key)
        self._cache[key] = value
        _mark_cache_hit("client")
        _record_cache_savings("client", value)
        return value

    def set(self, key: str, value: Any) -> None:
        if not self._enabled:
            return None
        if self.maxsize <= 0:
            return None
        if key in self._cache:
            self._cache.pop(key)
        self._cache[key] = value
        if len(self._cache) > self.maxsize:
            self._cache.popitem(last=False)
