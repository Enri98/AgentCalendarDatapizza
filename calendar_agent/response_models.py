from typing import Literal

from pydantic import BaseModel


class CalendarEvent(BaseModel):
    id: int
    title: str
    start: str
    end: str
    location: str | None = None
    notes: str | None = None


class CalendarResponse(BaseModel):
    mode: Literal["structured", "chat"] = "structured"
    action: Literal["list", "add", "update", "delete", "clarify", "other"]
    status: Literal["ok", "needs_clarification", "error"] = "ok"
    events: list[CalendarEvent] = []
    created_ids: list[int] = []
    updated_ids: list[int] = []
    deleted_ids: list[int] = []
    question: str | None = None
    message: str | None = None
