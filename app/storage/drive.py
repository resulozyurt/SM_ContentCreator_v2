"""
Google Drive storage backend.

Uploads generated images into the review folder (GOOGLE_DRIVE_REVIEW_FOLDER_ID)
using a service account (GOOGLE_DRIVE_CREDENTIALS_JSON — a file path or the raw
JSON). Humans then review the folder (checkpoint #3).
"""

from __future__ import annotations

import io
import json
import os

from app.config import get_settings
from app.storage.base import Storage, StorageError, StoredFile

_SCOPES = ["https://www.googleapis.com/auth/drive.file"]


class DriveStorage(Storage):
    """Storage backed by the Google Drive API."""

    name = "google_drive"

    def __init__(
        self, credentials_json: str | None = None, folder_id: str | None = None
    ) -> None:
        settings = get_settings()
        self._credentials_json = credentials_json or settings.google_drive_credentials_json
        self._folder_id = folder_id or settings.google_drive_review_folder_id
        if not self._credentials_json:
            raise StorageError("GOOGLE_DRIVE_CREDENTIALS_JSON is not set.")
        if not self._folder_id:
            raise StorageError("GOOGLE_DRIVE_REVIEW_FOLDER_ID is not set.")
        self._service = self._build_service()

    def _build_service(self):
        from google.oauth2 import service_account
        from googleapiclient.discovery import build

        raw = self._credentials_json
        try:
            if os.path.exists(raw):
                creds = service_account.Credentials.from_service_account_file(
                    raw, scopes=_SCOPES
                )
            else:
                creds = service_account.Credentials.from_service_account_info(
                    json.loads(raw), scopes=_SCOPES
                )
        except Exception as exc:  # noqa: BLE001
            raise StorageError(f"Invalid Drive credentials: {exc}") from exc

        # cache_discovery=False avoids a noisy warning and a file-cache dependency.
        return build("drive", "v3", credentials=creds, cache_discovery=False)

    def upload_image(
        self, filename: str, data: bytes, *, mime_type: str = "image/png"
    ) -> StoredFile:
        from googleapiclient.http import MediaIoBaseUpload

        media = MediaIoBaseUpload(io.BytesIO(data), mimetype=mime_type, resumable=False)
        metadata = {"name": filename, "parents": [self._folder_id]}
        try:
            created = (
                self._service.files()
                .create(
                    body=metadata,
                    media_body=media,
                    fields="id, webViewLink",
                    supportsAllDrives=True,
                )
                .execute()
            )
        except Exception as exc:  # noqa: BLE001
            raise StorageError(f"Drive upload failed: {exc}") from exc

        return StoredFile(
            id=created["id"],
            url=created.get("webViewLink", f"https://drive.google.com/file/d/{created['id']}/view"),
        )
