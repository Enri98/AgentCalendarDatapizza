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

## Running the App

Run the REPL CLI:
```bash
python -m calendar_agent
```

## Rules
- The assistant supports up to 15 conversation turns per session.
- Type `/exit` to end the session.
- Agent `max_steps` is set to 8.
- Memory is reset each time the application is run.
- Database is reserved at `./data/calendar.db`.
