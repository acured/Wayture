from __future__ import annotations

import json
import uuid
from pathlib import Path

from models import Attraction, PlannedStop, PostcardResponse
from services.ai import chat_completion, generate_image
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

    raw = await chat_completion(
        messages=[{"role": "user", "content": prompt}],
        temperature=cfg_text.get("temperature", 0.8),
    )

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

    image_bytes_list = await generate_image(
        prompt=img_prompt,
        size=cfg_img.get("size", "1024x1024"),
    )

    user_dir = STATIC_DIR / username
    user_dir.mkdir(parents=True, exist_ok=True)
    filename = f"postcard_{uuid.uuid4().hex[:8]}.png"
    filepath = user_dir / filename
    filepath.write_bytes(image_bytes_list[0])

    prompt_file = filepath.with_suffix(".txt")
    prompt_file.write_text(addition_prompt or "", encoding="utf-8")

    image_url = f"/static/{username}/{filename}"

    return PostcardResponse(
        username=username,
        title=title,
        greeting=greeting,
        stops=stops_list,
        farewell=farewell,
        image_url=image_url,
    )
