from __future__ import annotations

from typing import Any
from typing_extensions import TypedDict


class EmailThread(TypedDict):
    thread_id: str
    subject: str
    participants: list[str]
    messages: list[dict[str, Any]]  # {from, date, subject, body}
    needs_followup: bool
    followup_reason: str
    is_meeting_request: bool
    meeting_datetime: str   # ISO 8601, e.g. "2026-06-30T10:00:00"
    meeting_event_url: str  # set after calendar event is created
    draft_body: str
    draft_id: str           # set after save_drafts node


class AgentState(TypedDict):
    threads: list[EmailThread]
    run_summary: str
    errors: list[str]
