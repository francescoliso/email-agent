"""
Run once to authorize the agent: python -m gmail.auth
Stores a refresh token so subsequent runs are non-interactive.
"""

from __future__ import annotations

import os
import json
from pathlib import Path
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.compose",
]


def get_credentials(credentials_path: str, token_path: str) -> Credentials:
    creds_file = Path(credentials_path).expanduser()
    token_file = Path(token_path).expanduser()
    token_file.parent.mkdir(parents=True, exist_ok=True)

    creds: Optional[Credentials] = None

    if token_file.exists():
        creds = Credentials.from_authorized_user_file(str(token_file), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not creds_file.exists():
                raise FileNotFoundError(
                    f"Gmail credentials not found at {creds_file}.\n"
                    "Download OAuth 2.0 credentials from Google Cloud Console and save them there."
                )
            flow = InstalledAppFlow.from_client_secrets_file(str(creds_file), SCOPES)
            creds = flow.run_local_server(port=0)

        token_file.write_text(creds.to_json())

    return creds


if __name__ == "__main__":
    from config import settings
    creds = get_credentials(settings.gmail_credentials_path, settings.gmail_token_path)
    print(f"Auth successful. Token saved to {Path(settings.gmail_token_path).expanduser()}")
