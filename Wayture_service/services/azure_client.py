"""
Azure OpenAI 客户端工厂 — Chat 端点连接。
App Service 使用 System Assigned Managed Identity (DefaultAzureCredential)。
"""

from __future__ import annotations

from openai import AsyncAzureOpenAI

CHAT_AZURE_ENDPOINT = "https://aoai-svc-0.openai.azure.com/"
CHAT_API_VERSION = "2024-12-01-preview"
CHAT_DEPLOYMENT = "gpt-5.1"

_chat_client: AsyncAzureOpenAI | None = None


def _init_chat_client() -> AsyncAzureOpenAI:
    from azure.identity import DefaultAzureCredential, get_bearer_token_provider

    credential = DefaultAzureCredential()
    token_provider = get_bearer_token_provider(
        credential, "https://cognitiveservices.azure.com/.default"
    )
    return AsyncAzureOpenAI(
        azure_endpoint=CHAT_AZURE_ENDPOINT,
        azure_ad_token_provider=token_provider,
        api_version=CHAT_API_VERSION,
    )


def get_chat_client() -> tuple[AsyncAzureOpenAI, str]:
    global _chat_client
    if _chat_client is None:
        _chat_client = _init_chat_client()
    return _chat_client, CHAT_DEPLOYMENT
