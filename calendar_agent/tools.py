from datapizza.tools import tool

@tool
def list_events(start_iso: str, end_iso: str) -> str:
    """
    Lists calendar events within a specific ISO datetime range.
    
    Args:
        start_iso: Start of the range in ISO 8601 format.
        end_iso: End of the range in ISO 8601 format.
    """
    return "STUB: list_events NOT IMPLEMENTED YET"

@tool
def add_event(title: str, start_iso: str, end_iso: str, location: str = "", notes: str = "") -> str:
    """
    Adds a new event to the calendar.
    
    Args:
        title: Title of the event.
        start_iso: Start time in ISO 8601 format.
        end_iso: End time in ISO 8601 format.
        location: Optional location of the event.
        notes: Optional notes for the event.
    """
    return "STUB: add_event NOT IMPLEMENTED YET"

@tool
def update_event(
    event_id: int, 
    title: str | None = None, 
    start_iso: str | None = None, 
    end_iso: str | None = None, 
    location: str | None = None, 
    notes: str | None = None
) -> str:
    """
    Updates an existing calendar event.
    
    Args:
        event_id: The ID of the event to update.
        title: New title.
        start_iso: New start time.
        end_iso: New end time.
        location: New location.
        notes: New notes.
    """
    return f"STUB: update_event {event_id} NOT IMPLEMENTED YET"

@tool
def delete_events(event_ids: list[int]) -> str:
    """
    Deletes one or more calendar events by their IDs.
    
    Args:
        event_ids: List of event IDs to delete.
    """
    return f"STUB: delete_events {event_ids} NOT IMPLEMENTED YET"
