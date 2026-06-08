from __future__ import annotations

import json

from azure.storage.blob.aio import BlobServiceClient
from azure.core.exceptions import ResourceNotFoundError

STORAGE_ACCOUNT = "wayturestorage"

_client: BlobServiceClient | None = None


def _get_client() -> BlobServiceClient:
    global _client
    if _client is None:
        from azure.identity.aio import DefaultAzureCredential

        _client = BlobServiceClient(
            account_url=f"https://{STORAGE_ACCOUNT}.blob.core.windows.net",
            credential=DefaultAzureCredential(),
        )
    return _client


async def upload_blob(container, blob_path, data, content_type=None):
    from azure.storage.blob import ContentSettings
    kwargs = {"overwrite": True}
    if content_type:
        kwargs["content_settings"] = ContentSettings(content_type=content_type)
    blob = _get_client().get_blob_client(container, blob_path)
    await blob.upload_blob(data, **kwargs)


async def download_blob(container, blob_path):
    blob = _get_client().get_blob_client(container, blob_path)
    stream = await blob.download_blob()
    return await stream.readall()


async def read_json(container, blob_path):
    try:
        raw = await download_blob(container, blob_path)
        return json.loads(raw)
    except ResourceNotFoundError:
        return []


async def write_json(container, blob_path, obj):
    text = json.dumps(obj, ensure_ascii=False, indent=2)
    await upload_blob(container, blob_path, text.encode("utf-8"), content_type="application/json")


async def upload_text(container, blob_path, text):
    await upload_blob(container, blob_path, text.encode("utf-8"), content_type="text/plain; charset=utf-8")
