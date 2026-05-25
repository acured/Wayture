from __future__ import annotations

import json
import os

from azure.storage.blob.aio import BlobServiceClient
from azure.core.exceptions import ResourceNotFoundError

_client: BlobServiceClient | None = None


def _get_client() -> BlobServiceClient:
    global _client
    if _client is None:
        account = os.environ["AZURE_STORAGE_ACCOUNT"]
        sas = os.environ["AZURE_STORAGE_SAS_TOKEN"]
        _client = BlobServiceClient(
            account_url=f"https://{account}.blob.core.windows.net?{sas}",
        )
    return _client


async def upload_blob(
    container: str,
    blob_path: str,
    data: bytes,
    content_type: str | None = None,
) -> None:
    from azure.storage.blob import ContentSettings

    kwargs: dict = {"overwrite": True}
    if content_type:
        kwargs["content_settings"] = ContentSettings(content_type=content_type)

    blob = _get_client().get_blob_client(container, blob_path)
    await blob.upload_blob(data, **kwargs)


async def download_blob(container: str, blob_path: str) -> bytes:
    blob = _get_client().get_blob_client(container, blob_path)
    stream = await blob.download_blob()
    return await stream.readall()


async def read_json(container: str, blob_path: str) -> list | dict:
    try:
        raw = await download_blob(container, blob_path)
        return json.loads(raw)
    except ResourceNotFoundError:
        return []


async def write_json(container: str, blob_path: str, obj: list | dict) -> None:
    text = json.dumps(obj, ensure_ascii=False, indent=2)
    await upload_blob(container, blob_path, text.encode("utf-8"), content_type="application/json")


async def upload_text(container: str, blob_path: str, text: str) -> None:
    await upload_blob(
        container, blob_path, text.encode("utf-8"),
        content_type="text/plain; charset=utf-8",
    )


async def delete_blob(container: str, blob_path: str) -> None:
    blob = _get_client().get_blob_client(container, blob_path)
    try:
        await blob.delete_blob()
    except ResourceNotFoundError:
        pass
