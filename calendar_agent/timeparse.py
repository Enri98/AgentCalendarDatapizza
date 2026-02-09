import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

ROME_TZ = ZoneInfo("Europe/Rome")

def resolve_range(text: str, now: datetime) -> tuple[str, str] | None:
    """
    Parses a string to extract a time range (start and end).
    """
    text = text.lower()
    
    # Ensure now is aware in Rome TZ
    if now.tzinfo is None:
        now = now.replace(tzinfo=ROME_TZ)
    else:
        now = now.astimezone(ROME_TZ)
    
    start_dt = None
    end_dt = None

    # Base day range
    if "today" in text:
        start_dt = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_dt = start_dt + timedelta(days=1)
    elif "tomorrow" in text:
        start_dt = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        end_dt = start_dt + timedelta(days=1)
    elif "next week" in text:
        days_to_monday = (7 - now.weekday()) % 7
        if days_to_monday == 0: days_to_monday = 7
        start_dt = (now + timedelta(days=days_to_monday)).replace(hour=0, minute=0, second=0, microsecond=0)
        end_dt = start_dt + timedelta(days=7)
    elif "this week" in text:
        start_dt = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
        end_dt = start_dt + timedelta(days=7)
    
    if not start_dt:
        return None

    # Modifiers
    if "morning" in text:
        start_dt = start_dt.replace(hour=8)
        end_dt = start_dt.replace(hour=12)
    elif "afternoon" in text:
        start_dt = start_dt.replace(hour=12)
        end_dt = start_dt.replace(hour=18)
    elif "evening" in text:
        start_dt = start_dt.replace(hour=18)
        end_dt = start_dt.replace(hour=23)

    return start_dt.isoformat(), end_dt.isoformat()

def resolve_event_start_end(text: str, now: datetime) -> tuple[str, str] | None:
    """
    Parses a string to extract a specific event's start and end time.
    """
    text = text.lower()
    
    # Ensure now is aware in Rome TZ
    if now.tzinfo is None:
        now = now.replace(tzinfo=ROME_TZ)
    else:
        now = now.astimezone(ROME_TZ)
    
    # Identify base day
    base_day = None
    if "today" in text:
        base_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif "tomorrow" in text:
        base_day = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    elif "this week" in text or "next week" in text:
        # If week keyword, we need further clarification usually, 
        # but let's assume resolve_range handled it. 
        # Request says: If explicit time but no day keyword, return None.
        pass
    
    # If no day keyword found and there's a time pattern, return None to force clarification
    day_keywords = {"today", "tomorrow", "next week", "this week"}
    if not any(k in text for k in day_keywords):
        return None

    if not base_day:
        return None

    # Patterns
    match_range = re.search(r"(\d{1,2})(?::(\d{2}))?\s*-\s*(\d{1,2})(?::(\d{2}))?", text)
    if match_range:
        h1, m1, h2, m2 = match_range.groups()
        start = base_day.replace(hour=int(h1), minute=int(m1 or 0), tzinfo=ROME_TZ)
        end = base_day.replace(hour=int(h2), minute=int(m2 or 0), tzinfo=ROME_TZ)
        return start.isoformat(), end.isoformat()

    match_single = re.search(r"(?:at\s+)?(\d{1,2})(?::(\d{2}))?", text)
    if match_single:
        h, m = match_single.groups()
        start = base_day.replace(hour=int(h), minute=int(m or 0), tzinfo=ROME_TZ)
        end = start + timedelta(minutes=60)
        return start.isoformat(), end.isoformat()

    return None


