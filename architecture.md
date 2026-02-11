# Architecture Overview

This project is a local, terminal-based calendar assistant powered by Datapizza and Gemini. It runs a REPL that accepts user requests, calls tools to read/write a SQLite calendar database, and returns concise responses.

## Core Flow
1. `calendar_agent/__main__.py` boots the REPL, seeds the database, and runs the agent per turn.
   - If `CALENDAR_STRUCTURED_OUTPUT=1`, the session is capped at 2 user turns, memory is cleared after turn 2, and the REPL exits.
2. `calendar_agent/agent.py` wires the Datapizza `Agent`, client, memory, and tools.
   - Chooses chat vs structured system prompt based on `CALENDAR_STRUCTURED_OUTPUT`.
3. `calendar_agent/tools.py` implements calendar CRUD tools over SQLite and includes tool-level tracing spans.
   - In structured mode, tool outputs are JSON with ISO-8601 timestamps (with offset).
4. `calendar_agent/timeparse.py` parses natural language into date ranges for tool calls.
5. `calendar_agent/cache.py` provides an in-memory LRU client cache and emits cache hit telemetry.
 6. `calendar_agent/response_models.py` defines the structured response schema (Pydantic models).
 7. `calendar_agent/utils.py` provides shared helpers (e.g., env truthy parsing).

## Data Storage
- SQLite database at `data/calendar.db` (path configurable via `CALENDAR_DB_PATH`).

## Observability
- OpenTelemetry spans are emitted for agent execution, model generations, tool calls, and SQLite operations.
- Per-turn summaries are printed when `CALENDAR_TRACING=1`, including token usage, tool timing, and cache savings.

## Tests
- `tests/test_logic.py` covers CRUD and time parsing.
- `tests/test_cache.py` validates tool cache behavior and cache telemetry hooks.
- `tests/test_structured_tool_outputs.py` validates JSON tool outputs in structured mode.
