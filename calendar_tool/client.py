from __future__ import annotations

from datetime import datetime, timedelta
from googleapiclient.discovery import build

from gmail.auth import get_credentials
from config import settings


def _build_service():
    creds = get_credentials(settings.gmail_credentials_path, settings.gmail_token_path)
    return build("calendar", "v3", credentials=creds)


def create_event(
    summary: str,
    start_iso: str,
    attendees: list[str],
    duration_minutes: int = 60,
    description: str = "",
) -> str:
    """Create a Google Calendar event and return its URL."""
    service = _build_service()

    start = datetime.fromisoformat(start_iso.replace("Z", "+00:00"))
    end = start + timedelta(minutes=duration_minutes)

    event = {
        "summary": summary,
        "description": description,
        "start": {"dateTime": start.isoformat(), "timeZone": "Europe/Rome"},
        "end": {"dateTime": end.isoformat(), "timeZone": "Europe/Rome"},
        "attendees": [{"email": email} for email in attendees],
        "conferenceData": {
            "createRequest": {
                "requestId": f"meet-{start.timestamp()}",
                "conferenceSolutionKey": {"type": "hangoutsMeet"},
            }
        },
    }

    created = service.events().insert(
        calendarId="primary",
        body=event,
        conferenceDataVersion=1,
        sendUpdates="all",
    ).execute()

    return created.get("htmlLink", "")
