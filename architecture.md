# Architecture Overview

This project is a local, terminal-based calendar assistant powered by Datapizza and Gemini. It runs a REPL that accepts user requests, calls tools to read/write a SQLite calendar database, and returns concise responses.

## Core Flow
1. `calendar_agent/__main__.py` boots the REPL, seeds the database, and runs the agent per turn.
2. `calendar_agent/agent.py` wires the Datapizza `Agent`, client, memory, and tools.
3. `calendar_agent/tools.py` implements calendar CRUD tools over SQLite and includes tool-level tracing spans.
4. `calendar_agent/timeparse.py` parses natural language into date ranges for tool calls.
5. `calendar_agent/cache.py` provides an in-memory LRU client cache and emits cache hit telemetry.

## Data Storage
- SQLite database at `data/calendar.db` (path configurable via `CALENDAR_DB_PATH`).

## Observability
- OpenTelemetry spans are emitted for agent execution, model generations, tool calls, and SQLite operations.
- Per-turn summaries are printed when `CALENDAR_TRACING=1`, including token usage, tool timing, and cache savings.

## Tests
- `tests/test_logic.py` covers CRUD and time parsing.
- `tests/test_cache.py` validates tool cache behavior and cache telemetry hooks.
