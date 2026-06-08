from __future__ import annotations

from services.azure_client import get_chat_client


def _strip_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    return text


async def chat_completion(
    messages: list[dict],
    temperature: float = 0.7,
) -> str:
    client, deployment = get_chat_client()
    resp = await client.chat.completions.create(
        model=deployment,
        messages=messages,
        temperature=temperature,
    )
    return _strip_fences(resp.choices[0].message.content.strip())
