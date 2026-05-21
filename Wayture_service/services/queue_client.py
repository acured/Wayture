from __future__ import annotations

import base64
import json
import os

from azure.storage.queue import QueueClient

QUEUE_NAME = "image-tasks"
_client: QueueClient | None = None


def _get_client() -> QueueClient:
    global _client
    if _client is None:
        account = os.environ["AZURE_STORAGE_ACCOUNT"]
        sas = os.environ["AZURE_STORAGE_SAS_TOKEN"]
        _client = QueueClient(
            account_url=f"https://{account}.queue.core.windows.net?{sas}",
            queue_name=QUEUE_NAME,
        )
    return _client


def send_message(msg: dict) -> None:
    raw = json.dumps(msg, ensure_ascii=False)
    encoded = base64.b64encode(raw.encode("utf-8")).decode("utf-8")
    _get_client().send_message(encoded)


def receive_messages(max_messages: int = 1, visibility_timeout: int = 300):
    return _get_client().receive_messages(
        max_messages=max_messages,
        visibility_timeout=visibility_timeout,
    )


def delete_message(message) -> None:
    _get_client().delete_message(message)
