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
    draft_body: str
    draft_id: str  # set after save_drafts node


class AgentState(TypedDict):
    threads: list[EmailThread]
    run_summary: str
    errors: list[str]
