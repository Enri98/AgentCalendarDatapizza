# Calendar Assistant

In this project, I create a local Calendar Assistant built with Datapizza AI and Gemini.

It is a simple pet project that run an agent who will take care of your calendar. You interact with the agent through the Terminal.

## Setup

1. Create a virtual environment:
   ```bash
   py -3.11 -m venv .venv
   .venv\Scripts\activate
   ```
2. Install dependencies:
   ```bash
   pip install -e .
   ```
3. Set up environment variables:
   - Copy `.env.example` to `.env`.
   - Add your `GOOGLE_API_KEY`.
   - *Note: Set `DATAPIZZA_LOG_LEVEL` and `DATAPIZZA_AGENT_LOG_LEVEL` to `INFO` or `DEBUG` in `.env` if you need detailed execution logs.*
   - To see a per-turn Trace Summary in the console, set `CALENDAR_TRACING=1`.
   - Cache controls are available via `CALENDAR_CLIENT_CACHE_ENABLED`, `CALENDAR_CLIENT_CACHE_SIZE`, and `CALENDAR_TOOL_CACHE_ENABLED`.

## Running the App

Run the REPL CLI:
```bash
python -m calendar_agent
```

## Architecture
- See `architecture.md` for a brief overview of the project layout and data flow.

## Caching
- Client cache: an in-memory LRU attached to the Datapizza `GoogleClient`, reusing identical LLM calls within the same REPL session. Disable with `CALENDAR_CLIENT_CACHE_ENABLED=0` or adjust size with `CALENDAR_CLIENT_CACHE_SIZE`.
- Tool cache: `list_events` results are cached per `(start_iso, end_iso, DB_REVISION)`. Any `add_event`, `update_event`, or `delete_events` increments `DB_REVISION` and clears the cache. Disable with `CALENDAR_TOOL_CACHE_ENABLED=0`.

## Rules
- The assistant supports up to 15 conversation turns per session.
- Type `/exit` to end the session.
- Agent `max_steps` is set to 8.
- Memory is reset each time the application is run.
- Database is reserved at `./data/calendar.db`.

## Tracing
- Set `CALENDAR_TRACING=1` to print a per-turn trace summary.
- The summary includes model token usage, tool timing, and cache token savings.
