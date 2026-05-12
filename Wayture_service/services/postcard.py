from __future__ import annotations

import base64
import json
import os
import uuid
from pathlib import Path

from models import Attraction, PlannedStop, PostcardResponse
from services.azure_client import get_postcard_client, get_vision_client
from services.config import get_prompts, render_prompt

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


async def generate_postcard(
    username: str,
    route_plan: list[PlannedStop],
    attractions: list[Attraction],
    addition_prompt: str = "",
) -> PostcardResponse:
    route_info = [
        {"order": s.order, "name": s.attraction.name, "tips": s.tips}
        for s in route_plan
    ]
    spots = [
        {"name": a.name, "description": a.description, "field": a.field, "cost": a.cost}
        for a in attractions
    ]

    # ── 1. 用 chat 模型生成明信片文案 ────────────────────────────
    cfg_text = get_prompts()["postcard"]
    prompt = render_prompt(
        "postcard",
        route_info=json.dumps(route_info, ensure_ascii=False),
        spots=json.dumps(spots, ensure_ascii=False),
    )

    chat_client, chat_deploy = get_vision_client()
    resp = await chat_client.chat.completions.create(
        model=chat_deploy,
        messages=[{"role": "user", "content": prompt}],
        temperature=cfg_text.get("temperature", 0.8),
    )

    raw = resp.choices[0].message.content.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()

    data = json.loads(raw)

    title = data.get("title", "")
    greeting = data.get("greeting", "")
    stops_list = data.get("stops", [])
    farewell = data.get("farewell", "")

    # ── 2. 用 image 模型生成明信片图片 ───────────────────────────
    stops_summary = "、".join(s.get("name", "") for s in stops_list)

    cfg_img = get_prompts()["postcard_image"]
    img_prompt = render_prompt(
        "postcard_image",
        title=title,
        greeting=greeting,
        stops_summary=stops_summary,
        farewell=farewell,
        addition_prompt=addition_prompt,
    )

    img_client, img_deploy = get_postcard_client()
    img_resp = await img_client.images.generate(
        model=img_deploy,
        prompt=img_prompt,
        size=cfg_img.get("size", "1024x1024"),
        n=1,
    )

    image_data = img_resp.data[0]
    user_dir = STATIC_DIR / username
    user_dir.mkdir(parents=True, exist_ok=True)
    filename = f"postcard_{uuid.uuid4().hex[:8]}.png"
    filepath = user_dir / filename

    if hasattr(image_data, "b64_json") and image_data.b64_json:
        filepath.write_bytes(base64.b64decode(image_data.b64_json))
    elif hasattr(image_data, "url") and image_data.url:
        import httpx
        async with httpx.AsyncClient() as http:
            dl = await http.get(image_data.url)
            filepath.write_bytes(dl.content)

    image_url = f"/static/{username}/{filename}"

    return PostcardResponse(
        username=username,
        title=title,
        greeting=greeting,
        stops=stops_list,
        farewell=farewell,
        image_url=image_url,
    )
