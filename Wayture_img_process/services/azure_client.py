from __future__ import annotations

from azure.identity import ManagedIdentityCredential, get_bearer_token_provider
from openai import AzureOpenAI

AZURE_ENDPOINT = "https://aoai-svc-0.openai.azure.com/"
API_VERSION = "2025-04-01-preview"
DEPLOYMENT = "gpt-image-2-01"
OPENAI_MI_CLIENT_ID = "dc1352c5-927a-4fa1-93c4-eecb03417716"

_client: AzureOpenAI | None = None


def get_image_client() -> tuple[AzureOpenAI, str]:
    global _client
    if _client is None:
        credential = ManagedIdentityCredential(client_id=OPENAI_MI_CLIENT_ID)
        token_provider = get_bearer_token_provider(
            credential, "https://cognitiveservices.azure.com/.default"
        )
        _client = AzureOpenAI(
            azure_endpoint=AZURE_ENDPOINT,
            azure_ad_token_provider=token_provider,
            api_version=API_VERSION,
        )
    return _client, DEPLOYMENT
