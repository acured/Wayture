"""
Azure OpenAI 客户端工厂 — 统一管理 chat 和 image 两个端点的连接。
从 .env 解析 Azure endpoint URL，自动提取 base_url / deployment / api-version。
"""

from __future__ import annotations

import os
import re
from urllib.parse import urlparse, parse_qs

from dotenv import load_dotenv
from openai import AsyncAzureOpenAI

load_dotenv()


def _parse_azure_endpoint(url: str) -> tuple[str, str, str]:
    """
    从完整的 Azure OpenAI URL 解析出:
      - azure_endpoint  (https://xxx.openai.azure.com)
      - deployment      (模型部署名)
      - api_version     (api-version 参数)

    支持格式:
      https://<resource>.openai.azure.com/openai/deployments/<deploy>/chat/completions?api-version=...
      https://<resource>.cognitiveservices.azure.com/openai/deployments/<deploy>/images/generations?api-version=...
    """
    parsed = urlparse(url)
    azure_endpoint = f"{parsed.scheme}://{parsed.hostname}"

    deploy_match = re.search(r"/deployments/([^/]+)", parsed.path)
    deployment = deploy_match.group(1) if deploy_match else ""

    qs = parse_qs(parsed.query)
    api_version = qs.get("api-version", ["2024-10-21"])[0]

    return azure_endpoint, deployment, api_version


# ── Vision 客户端（chat completions） ───────────────────────────

_vision_client: AsyncAzureOpenAI | None = None
_vision_deployment: str = ""


def get_chat_client() -> tuple[AsyncAzureOpenAI, str]:
    global _vision_client, _vision_deployment
    if _vision_client is None:
        url = os.getenv("VITE_VISION_API_ENDPOINT", "")
        token = os.getenv("VITE_VISION_API_TOKEN", "")
        endpoint, deploy, version = _parse_azure_endpoint(url)
        _vision_deployment = deploy or "gpt-4o"
        _vision_client = AsyncAzureOpenAI(
            azure_endpoint=endpoint,
            api_key=token,
            api_version=version,
        )
    return _vision_client, _vision_deployment


# ── Postcard / Image 客户端（image generation） ─────────────────

# _postcard_client: AsyncAzureOpenAI | None = None
# _postcard_deployment: str = ""
#
#
# def get_image_client() -> tuple[AsyncAzureOpenAI, str]:
#     global _postcard_client, _postcard_deployment
#     if _postcard_client is None:
#         url = os.getenv("VITE_POSTCARD_API_ENDPOINT", "")
#         token = os.getenv("VITE_POSTCARD_API_TOKEN", "")
#         endpoint, deploy, version = _parse_azure_endpoint(url)
#         _postcard_deployment = deploy or "gpt-image-1"
#         _postcard_client = AsyncAzureOpenAI(
#             azure_endpoint=endpoint,
#             api_key=token,
#             api_version=version,
#         )
#     return _postcard_client, _postcard_deployment

IMAGE_AZURE_ENDPOINT = "https://aoai-svc-0.openai.azure.com/"
IMAGE_MANAGED_IDENTITY_CLIENT_ID = "dc1352c5-927a-4fa1-93c4-eecb03417716"
IMAGE_API_VERSION = "2025-04-01-preview"
IMAGE_DEPLOYMENT = "gpt-image-2-01"

_image_client: "AzureOpenAI | None" = None


def get_image_client() -> tuple["AzureOpenAI", str]:
    global _image_client
    if _image_client is None:
        from azure.identity import ManagedIdentityCredential, DefaultAzureCredential, get_bearer_token_provider
        from openai import AzureOpenAI

        try:
            credential = ManagedIdentityCredential(client_id=IMAGE_MANAGED_IDENTITY_CLIENT_ID)
            token_provider = get_bearer_token_provider(
                credential, "https://cognitiveservices.azure.com/.default"
            )
        except Exception:
            credential = DefaultAzureCredential()
            token_provider = get_bearer_token_provider(
                credential, "https://cognitiveservices.azure.com/.default"
            )
        _image_client = AzureOpenAI(
            azure_endpoint=IMAGE_AZURE_ENDPOINT,
            azure_ad_token_provider=token_provider,
            api_version=IMAGE_API_VERSION,
        )
    return _image_client, IMAGE_DEPLOYMENT
