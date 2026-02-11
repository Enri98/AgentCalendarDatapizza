from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from datapizza.tracing import console
from rich.console import Group
from rich.panel import Panel
from rich.table import Table


@dataclass
class ToolStats:
    count: int = 0
    total_ms: float = 0.0


@dataclass
class CacheSavings:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cached_tokens: int = 0
    total_tokens: int = 0


def _span_duration_ms(span: Any) -> float:
    start = getattr(span, "start_time", None)
    end = getattr(span, "end_time", None)
    if not start or not end:
        return 0.0
    return round((end - start) / 1_000_000, 2)


def _collect_tool_stats(spans: list[Any]) -> dict[str, ToolStats]:
    stats: dict[str, ToolStats] = {}
    for span in spans:
        if span.attributes.get("type") != "tool":
            continue
        name = span.name or "tool"
        duration_ms = _span_duration_ms(span)
        entry = stats.setdefault(name, ToolStats())
        entry.count += 1
        entry.total_ms += duration_ms
    return stats


def _collect_cache_savings(spans: list[Any]) -> CacheSavings:
    savings = CacheSavings()
    for span in spans:
        for event in getattr(span, "events", []) or []:
            if getattr(event, "name", "") != "cache.hit":
                continue
            attrs = getattr(event, "attributes", {}) or {}
            savings.prompt_tokens += int(attrs.get("cache.saved_prompt_tokens", 0) or 0)
            savings.completion_tokens += int(
                attrs.get("cache.saved_completion_tokens", 0) or 0
            )
            savings.cached_tokens += int(attrs.get("cache.saved_cached_tokens", 0) or 0)
            savings.total_tokens += int(attrs.get("cache.saved_total_tokens", 0) or 0)
    return savings


def summarize_spans(spans: list[Any]) -> dict[str, Any]:
    tool_stats = _collect_tool_stats(spans)
    total_tool_ms = round(sum(s.total_ms for s in tool_stats.values()), 2)
    tool_calls = sum(s.count for s in tool_stats.values())
    cache_savings = _collect_cache_savings(spans)
    return {
        "tool_stats": tool_stats,
        "tool_calls": tool_calls,
        "tool_total_ms": total_tool_ms,
        "cache_savings": cache_savings,
    }


def render_turn_summary(
    summary: dict[str, Any],
    *,
    duration_ms: float | None = None,
    usage: Any | None = None,
) -> None:
    tool_stats: dict[str, ToolStats] = summary.get("tool_stats", {})
    cache_savings: CacheSavings = summary.get("cache_savings", CacheSavings())

    sections = []

    if duration_ms is not None:
        sections.append(f"Turn Duration: {round(duration_ms, 2)} ms")

    if usage is not None:
        prompt_tokens = int(getattr(usage, "prompt_tokens", 0) or 0)
        completion_tokens = int(getattr(usage, "completion_tokens", 0) or 0)
        cached_tokens = int(getattr(usage, "cached_tokens", 0) or 0)
        total_tokens = prompt_tokens + completion_tokens + cached_tokens
        sections.append(
            "Tokens Used: "
            f"{prompt_tokens} prompt, {completion_tokens} completion, "
            f"{cached_tokens} cached, {total_tokens} total"
        )

    if cache_savings.total_tokens > 0:
        sections.append(
            "Tokens Saved (Cache): "
            f"{cache_savings.prompt_tokens} prompt, "
            f"{cache_savings.completion_tokens} completion, "
            f"{cache_savings.cached_tokens} cached, "
            f"{cache_savings.total_tokens} total"
        )

    tool_table = None
    if tool_stats:
        tool_table = Table(title="Tool Timing")
        tool_table.add_column("Tool")
        tool_table.add_column("Calls")
        tool_table.add_column("Total ms")
        for name, stats in tool_stats.items():
            tool_table.add_row(name, str(stats.count), f"{round(stats.total_ms, 2)}")

    if not sections and tool_table is None:
        return

    panel = Panel(
        Group(*sections, tool_table if tool_table else ""),
        title="Turn Telemetry",
    )
    console.print(panel)
