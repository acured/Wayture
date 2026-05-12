from __future__ import annotations

import base64
import json
import os

from models import Attraction
from services.azure_client import get_vision_client
from services.config import get_prompts, render_prompt


async def classify_image(
    image_path: str,
    map_meta: list[Attraction],
) -> dict:
    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()

    ext = os.path.splitext(image_path)[1].lower().lstrip(".")
    mime_map = {"jpg": "jpeg", "jpeg": "jpeg", "png": "png", "gif": "gif", "webp": "webp"}
    mime = mime_map.get(ext, "jpeg")

    spots = [
        {"id": a.id, "name": a.name, "description": a.description, "field": a.field}
        for a in map_meta
    ]

    cfg = get_prompts()["vision_classify"]
    prompt = render_prompt(
        "vision_classify",
        spots=json.dumps(spots, ensure_ascii=False),
    )

    client, deployment = get_vision_client()
    resp = await client.chat.completions.create(
        model=deployment,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/{mime};base64,{b64}"},
                    },
                ],
            }
        ],
        temperature=cfg.get("temperature", 0.3),
    )

    raw = resp.choices[0].message.content.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()

    return json.loads(raw)
