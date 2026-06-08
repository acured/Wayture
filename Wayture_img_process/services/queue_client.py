from __future__ import annotations

import base64
import json
import os

from azure.identity import ManagedIdentityCredential, DefaultAzureCredential
from azure.storage.queue import QueueClient
from dotenv import load_dotenv

load_dotenv()

STORAGE_ACCOUNT = os.getenv("STORAGE_ACCOUNT", "wayturestorage")
QUEUE_NAME = "image-tasks"

_client: QueueClient | None = None


def _get_client() -> QueueClient:
    global _client
    if _client is None:
        mi_client_id = os.getenv("MI_CLIENT_ID", "")
        try:
            credential = ManagedIdentityCredential(client_id=mi_client_id) if mi_client_id else DefaultAzureCredential()
        except Exception:
            credential = DefaultAzureCredential()
        _client = QueueClient(
            account_url=f"https://{STORAGE_ACCOUNT}.queue.core.windows.net",
            queue_name=QUEUE_NAME,
            credential=credential,
        )
    return _client


def receive_messages(max_messages=1, visibility_timeout=300):
    return _get_client().receive_messages(
        max_messages=max_messages,
        visibility_timeout=visibility_timeout,
    )


def delete_message(message):
    _get_client().delete_message(message)
