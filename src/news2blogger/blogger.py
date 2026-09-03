from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

BLOGGER_SCOPE = ["https://www.googleapis.com/auth/blogger"]


def select_single_blog_id(blogs: list[dict[str, Any]]) -> str:
    available = [blog for blog in blogs if str(blog.get("id", "")).strip()]
    if not available:
        raise ValueError(
            "Google Blogger returned no accessible blogs for the authorized account"
        )
    if len(available) > 1:
        choices = ", ".join(
            f"{blog.get('name', 'Unnamed')} ({blog['id']})" for blog in available
        )
        raise ValueError(
            "Google Blogger returned multiple blogs; set BLOGGER_BLOG_ID to choose one: "
            f"{choices}"
        )
    return str(available[0]["id"])


class BloggerClient:
    def __init__(self, client_secrets: Path, token_file: Path) -> None:
        self.client_secrets = client_secrets
        self.token_file = token_file
        self.service = build("blogger", "v3", credentials=self._credentials())

    def _credentials(self) -> Credentials:
        credentials: Credentials | None = None
        if self.token_file.exists():
            credentials = Credentials.from_authorized_user_file(
                str(self.token_file), BLOGGER_SCOPE
            )
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        if not credentials or not credentials.valid:
            if not self.client_secrets.exists():
                raise FileNotFoundError(
                    f"Blogger OAuth credentials not found: {self.client_secrets}"
                )
            flow = InstalledAppFlow.from_client_secrets_file(
                str(self.client_secrets), BLOGGER_SCOPE
            )
            credentials = flow.run_local_server(port=0)
        self.token_file.parent.mkdir(parents=True, exist_ok=True)
        self.token_file.write_text(credentials.to_json(), encoding="utf-8")
        os.chmod(self.token_file, 0o600)
        return credentials

    def list_blogs(self) -> list[dict[str, Any]]:
        response = self.service.blogs().listByUser(userId="self").execute()
        return response.get("items", [])

    def resolve_blog_id(self, configured_blog_id: str | None) -> str:
        if configured_blog_id:
            return configured_blog_id
        return select_single_blog_id(self.list_blogs())

    def create_post(
        self, blog_id: str, title: str, content: str, *, draft: bool = True
    ) -> dict[str, Any]:
        body = {"kind": "blogger#post", "title": title, "content": content}
        return (
            self.service.posts()
            .insert(blogId=blog_id, body=body, isDraft=draft, fetchBody=False)
            .execute()
        )
