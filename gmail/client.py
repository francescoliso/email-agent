import base64
import email as email_lib
from datetime import datetime, timedelta, timezone
from typing import Any

from googleapiclient.discovery import build

from gmail.auth import get_credentials
from config import settings


def _build_service():
    creds = get_credentials(settings.gmail_credentials_path, settings.gmail_token_path)
    return build("gmail", "v1", credentials=creds)


def _decode_body(payload: dict) -> str:
    """Recursively extract plain-text body from a message payload."""
    mime_type = payload.get("mimeType", "")
    if mime_type == "text/plain":
        data = payload.get("body", {}).get("data", "")
        return base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")
    if mime_type.startswith("multipart/"):
        for part in payload.get("parts", []):
            text = _decode_body(part)
            if text:
                return text
    return ""


def _parse_headers(headers: list[dict]) -> dict[str, str]:
    return {h["name"].lower(): h["value"] for h in headers}


def fetch_threads(days_back: int = 7) -> list[dict[str, Any]]:
    """Return email threads from the past `days_back` days, excluding sent/drafts/spam/trash."""
    service = _build_service()
    since = (datetime.now(timezone.utc) - timedelta(days=days_back)).strftime("%Y/%m/%d")
    query = f"after:{since} -in:sent -in:drafts -in:spam -in:trash"

    result = service.users().threads().list(userId="me", q=query).execute()
    thread_stubs = result.get("threads", [])

    threads = []
    for stub in thread_stubs:
        thread = service.users().threads().get(userId="me", id=stub["id"], format="full").execute()
        messages = []
        participants: set[str] = set()

        for msg in thread.get("messages", []):
            headers = _parse_headers(msg["payload"].get("headers", []))
            sender = headers.get("from", "")
            participants.add(sender)
            messages.append({
                "from": sender,
                "date": headers.get("date", ""),
                "subject": headers.get("subject", "(no subject)"),
                "body": _decode_body(msg["payload"]),
            })

        subject = messages[0]["subject"] if messages else "(no subject)"
        threads.append({
            "thread_id": stub["id"],
            "subject": subject,
            "participants": list(participants),
            "messages": messages,
            "needs_followup": False,
            "followup_reason": "",
            "draft_body": "",
            "draft_id": "",
        })

    return threads


def create_draft(thread_id: str, to: str, subject: str, body: str) -> str:
    """Create a Gmail draft reply and return its draft ID."""
    service = _build_service()

    raw_message = (
        f"To: {to}\r\n"
        f"Subject: Re: {subject}\r\n"
        f"Content-Type: text/plain; charset=utf-8\r\n\r\n"
        f"{body}"
    )
    encoded = base64.urlsafe_b64encode(raw_message.encode("utf-8")).decode("utf-8")

    draft = service.users().drafts().create(
        userId="me",
        body={"message": {"raw": encoded, "threadId": thread_id}},
    ).execute()

    return draft["id"]
