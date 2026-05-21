from __future__ import annotations

import json
import uuid
from pathlib import Path

from models import Attraction, PlannedStop, PostcardResponse
from services.ai import chat_completion, generate_image
from services.blob_storage import upload_blob, upload_text, read_json
from services.config import get_prompts, render_prompt

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


async def prepare_postcard(
    username: str,
    route_plan: list[PlannedStop],
    attractions: list[Attraction],
    addition_prompt: str = "",
) -> tuple[PostcardResponse, dict]:
    route_info = [
        {"order": s.order, "name": s.attraction.name, "tips": s.tips}
        for s in route_plan
    ]
    spots = [
        {"name": a.name, "description": a.description, "field": a.field, "cost": a.cost}
        for a in attractions
    ]

    # ── 1. 用 chat 模型生成明信片文案（同步，快速）────────────────
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

    # ── 2. 构建 image prompt（不执行生成）─────────────────────────
    stops_summary = "、".join(s.get("name", "") for s in stops_list)

    attr_by_name = {a.name: a for a in attractions}
    cards: list[str] = []
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

    await upload_text("data", f"{username}/postcard/image_prompt.txt", img_prompt)

    task_data = {
        "prompt": img_prompt,
        "size": cfg_img.get("size", "1024x1024"),
        "postcard_data": {
            "title": title,
            "greeting": greeting,
            "stops": stops_list,
            "farewell": farewell,
        },
        "addition_prompt": addition_prompt,
    }

    response = PostcardResponse(
        username=username,
        title=title,
        greeting=greeting,
        stops=stops_list,
        farewell=farewell,
        image_url="",
    )

    return response, task_data


async def execute_postcard_task(username: str, task_data: dict) -> dict:
    prompt = task_data["prompt"]
    size = task_data.get("size", "1024x1024")

    image_bytes_list = await generate_image(prompt=prompt, size=size)

    filename = f"{uuid.uuid4().hex[:8]}.png"
    await upload_blob("data", f"{username}/postcard/{filename}", image_bytes_list[0], content_type="image/png")

    addition_prompt = task_data.get("addition_prompt", "")
    prompt_txt_name = filename.replace(".png", ".txt")
    await upload_text("data", f"{username}/postcard/{prompt_txt_name}", addition_prompt or "")

    image_url = f"/static/{username}/postcard/{filename}"

    return {"image_url": image_url}
