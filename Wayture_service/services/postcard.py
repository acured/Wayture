from __future__ import annotations

import json
import uuid
from pathlib import Path

from models import Attraction, PlannedStop, PostcardResponse
from services.ai import chat_completion, generate_image
from services.blob_storage import upload_blob, upload_text
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

    await upload_text("data", f"{username}/postcard/chat_prompt.txt", prompt)

    data = json.loads(raw)

    title = data.get("title", "")
    greeting = data.get("greeting", "")
    tour_text = data.get("tour_text", "")
    stops_list = data.get("stops", [])
    farewell = data.get("farewell", "")

    # ── 2. 用 image 模型生成明信片图片 ───────────────────────────
    stops_summary = "、".join(s.get("name", "") for s in stops_list)

    attr_by_name = {a.name: a for a in attractions}
    cards: list[str] = []
    input_images: list[bytes] = []
    photo_idx = 1
    for i, stop in enumerate(stops_list, 1):
        name = stop.get("name", "")
        attr = attr_by_name.get(name)
        if attr:
            card = (
                f"-「{i}」：「项目名称：{attr.name}」、"
                f"「项目介绍：{attr.description}」、"
                f"「建议时长：{attr.cost}」、"
                f"「项目标签:{attr.field}」、"
                f"「景点照片：图{photo_idx}是景点照片」"
            )
            photo_dir = STATIC_DIR / "map_data" / str(attr.id)
            if photo_dir.exists():
                photos = sorted(
                    p for p in photo_dir.iterdir()
                    if p.suffix.lower() in (".jpg", ".jpeg", ".png")
                )
                if photos:
                    input_images.append(photos[0].read_bytes())
                    photo_idx += 1
        else:
            card = f"-「{i}」：「项目名称：{name}」"
        cards.append(card)
    stops_cards = "\n".join(cards)

    cfg_img = get_prompts()["postcard_image"]
    img_prompt = render_prompt(
        "postcard_image",
        route_info=tour_text,
        stops_summary=stops_summary,
        stops_cards=stops_cards,
        farewell=farewell,
        addition_prompt=addition_prompt,
    )

    image_bytes_list = await generate_image(
        prompt=img_prompt,
        size=cfg_img.get("size", "1024x1024"),
        input_images=input_images if input_images else None,
    )

    await upload_text("data", f"{username}/postcard/image_prompt.txt", img_prompt)

    filename = f"postcard_{uuid.uuid4().hex[:8]}.png"
    await upload_blob("data", f"{username}/{filename}", image_bytes_list[0], content_type="image/png")

    prompt_txt_name = filename.replace(".png", ".txt")
    await upload_text("data", f"{username}/{prompt_txt_name}", addition_prompt or "")

    image_url = f"/static/{username}/{filename}"

    return PostcardResponse(
        username=username,
        title=title,
        greeting=greeting,
        stops=stops_list,
        farewell=farewell,
        image_url=image_url,
    )
