from __future__ import annotations

import json

from azure.storage.queue import QueueClient

STORAGE_ACCOUNT = "wayturestorage"
QUEUE_NAME = "image-tasks"

_client: QueueClient | None = None


def _get_client() -> QueueClient:
    global _client
    if _client is None:
        from azure.identity import DefaultAzureCredential

        _client = QueueClient(
            account_url=f"https://{STORAGE_ACCOUNT}.queue.core.windows.net",
            queue_name=QUEUE_NAME,
            credential=DefaultAzureCredential(),
        )
    return _client


def receive_messages(max_messages=1, visibility_timeout=300):
    return _get_client().receive_messages(
        max_messages=max_messages,
        visibility_timeout=visibility_timeout,
    )


def delete_message(message):
    _get_client().delete_message(message)
