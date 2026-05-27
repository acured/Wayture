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

# ── Chat (Vision) 常量 ────────────────────────────────────────
CHAT_MANAGED_IDENTITY_CLIENT_ID = ""
CHAT_AZURE_ENDPOINT = ""
CHAT_API_VERSION = ""
CHAT_DEPLOYMENT = ""

# ── Image 常量 ────────────────────────────────────────────────
IMAGE_MANAGED_IDENTITY_CLIENT_ID = "dc1352c5-927a-4fa1-93c4-eecb03417716"
IMAGE_AZURE_ENDPOINT = "https://aoai-svc-0.openai.azure.com/"
IMAGE_API_VERSION = "2025-04-01-preview"
IMAGE_DEPLOYMENT = "gpt-image-2-01"


# ── 工具函数 ──────────────────────────────────────────────────

def _parse_azure_endpoint(url: str) -> tuple[str, str, str]:
    """
    从完整的 Azure OpenAI URL 解析出:
      - azure_endpoint  (https://xxx.openai.azure.com)
      - deployment      (模型部署名)
      - api_version     (api-version 参数)
    """
    parsed = urlparse(url)
    azure_endpoint = f"{parsed.scheme}://{parsed.hostname}"

    deploy_match = re.search(r"/deployments/([^/]+)", parsed.path)
    deployment = deploy_match.group(1) if deploy_match else ""

    qs = parse_qs(parsed.query)
    api_version = qs.get("api-version", ["2024-10-21"])[0]

    return azure_endpoint, deployment, api_version


# ── Chat 客户端（chat completions） ───────────────────────────

_chat_client: AsyncAzureOpenAI | None = None
_chat_deployment: str = ""


def _init_chat_client_with_key() -> tuple[AsyncAzureOpenAI, str]:
    url = os.getenv("VITE_VISION_API_ENDPOINT", "")
    token = os.getenv("VITE_VISION_API_TOKEN", "")
    endpoint, deploy, version = _parse_azure_endpoint(url)
    deployment = deploy or "gpt-4o"
    client = AsyncAzureOpenAI(
        azure_endpoint=endpoint,
        api_key=token,
        api_version=version,
    )
    return client, deployment


def _init_chat_client_with_mi() -> tuple[AsyncAzureOpenAI, str]:
    from azure.identity import ManagedIdentityCredential, DefaultAzureCredential, get_bearer_token_provider

    try:
        credential = ManagedIdentityCredential(client_id=CHAT_MANAGED_IDENTITY_CLIENT_ID) if CHAT_MANAGED_IDENTITY_CLIENT_ID else DefaultAzureCredential()
        token_provider = get_bearer_token_provider(
            credential, "https://cognitiveservices.azure.com/.default"
        )
    except Exception:
        credential = DefaultAzureCredential()
        token_provider = get_bearer_token_provider(
            credential, "https://cognitiveservices.azure.com/.default"
        )
    client = AsyncAzureOpenAI(
        azure_endpoint=CHAT_AZURE_ENDPOINT,
        azure_ad_token_provider=token_provider,
        api_version=CHAT_API_VERSION,
    )
    return client, CHAT_DEPLOYMENT or "gpt-4o"


def get_chat_client() -> tuple[AsyncAzureOpenAI, str]:
    global _chat_client, _chat_deployment
    if _chat_client is None:
        _chat_client, _chat_deployment = _init_chat_client_with_key()
    return _chat_client, _chat_deployment


# ── Image 客户端（image generation） ──────────────────────────

_image_client: "AzureOpenAI | None" = None


def _init_image_client_with_key() -> tuple["AzureOpenAI", str]:
    from openai import AzureOpenAI

    url = os.getenv("VITE_POSTCARD_API_ENDPOINT", "")
    token = os.getenv("VITE_POSTCARD_API_TOKEN", "")
    endpoint, deploy, version = _parse_azure_endpoint(url)
    deployment = deploy or "gpt-image-1"
    client = AzureOpenAI(
        azure_endpoint=endpoint,
        api_key=token,
        api_version=version,
    )
    return client, deployment


def _init_image_client_with_mi() -> tuple["AzureOpenAI", str]:
    from azure.identity import ManagedIdentityCredential, DefaultAzureCredential, get_bearer_token_provider
    from openai import AzureOpenAI

    try:
        credential = ManagedIdentityCredential(client_id=IMAGE_MANAGED_IDENTITY_CLIENT_ID) if IMAGE_MANAGED_IDENTITY_CLIENT_ID else DefaultAzureCredential()
        token_provider = get_bearer_token_provider(
            credential, "https://cognitiveservices.azure.com/.default"
        )
    except Exception:
        credential = DefaultAzureCredential()
        token_provider = get_bearer_token_provider(
            credential, "https://cognitiveservices.azure.com/.default"
        )
    client = AzureOpenAI(
        azure_endpoint=IMAGE_AZURE_ENDPOINT,
        azure_ad_token_provider=token_provider,
        api_version=IMAGE_API_VERSION,
    )
    return client, IMAGE_DEPLOYMENT


def get_image_client() -> tuple["AzureOpenAI", str]:
    global _image_client
    if _image_client is None:
        _image_client, _image_deployment = _init_image_client_with_mi()
    return _image_client, _image_deployment
