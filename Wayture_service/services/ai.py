from __future__ import annotations

import base64
import io

from services.azure_client import get_image_client, get_chat_client


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


async def generate_image(
    prompt: str,
    *,
    size: str = "1024x1024",
    input_images: list[bytes] | None = None,
    n: int = 1,
    quality: str | None = None,
) -> list[bytes]:
    client, deployment = get_image_client()

    if input_images is not None:
        image_files = [io.BytesIO(img) for img in input_images]
        for f in image_files:
            f.name = "input.png"
        resp = await client.images.edit(
            model=deployment,
            image=image_files if len(image_files) > 1 else image_files[0],
            prompt=prompt,
            n=n,
            size=size,
        )
    else:
        kwargs: dict = dict(model=deployment, prompt=prompt, size=size, n=n)
        if quality is not None:
            kwargs["quality"] = quality
        resp = await client.images.generate(**kwargs)

    results: list[bytes] = []
    for item in resp.data:
        if hasattr(item, "b64_json") and item.b64_json:
            results.append(base64.b64decode(item.b64_json))
        elif hasattr(item, "url") and item.url:
            import httpx

            async with httpx.AsyncClient() as http:
                dl = await http.get(item.url)
                results.append(dl.content)
    return results
