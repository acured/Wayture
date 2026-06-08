from __future__ import annotations

import os

from azure.identity import ManagedIdentityCredential, DefaultAzureCredential, get_bearer_token_provider
from dotenv import load_dotenv
from openai import AzureOpenAI

load_dotenv()

AZURE_ENDPOINT = "https://aoai-svc-0.openai.azure.com/"
API_VERSION = "2025-04-01-preview"
DEPLOYMENT = "gpt-image-2-01"

_client: AzureOpenAI | None = None


def get_image_client() -> tuple[AzureOpenAI, str]:
    global _client
    if _client is None:
        mi_client_id = os.getenv("MI_CLIENT_ID", "")
        try:
            credential = ManagedIdentityCredential(client_id=mi_client_id) if mi_client_id else DefaultAzureCredential()
            token_provider = get_bearer_token_provider(
                credential, "https://cognitiveservices.azure.com/.default"
            )
        except Exception:
            credential = DefaultAzureCredential()
            token_provider = get_bearer_token_provider(
                credential, "https://cognitiveservices.azure.com/.default"
            )
        _client = AzureOpenAI(
            azure_endpoint=AZURE_ENDPOINT,
            azure_ad_token_provider=token_provider,
            api_version=API_VERSION,
        )
    return _client, DEPLOYMENT
