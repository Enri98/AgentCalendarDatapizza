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
