from __future__ import annotations

import json
import uuid
from pathlib import Path

from models import Attraction, PlannedStop, PostcardResponse
from services.ai import chat_completion, generate_image
from services.blob_storage import upload_blob, upload_text, read_json
from services.config import get_map_meta, get_prompts, render_prompt

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

    server_attrs = {a.name: a for a in get_map_meta()}
    attr_by_name = {a.name: a for a in attractions}

    cards: list[str] = []
    ref_image_paths: list[str] = []
    ref_image_descs: list[str] = []
    photo_idx = 1
    for i, stop in enumerate(stops_list, 1):
        name = stop.get("name", "")
        attr = attr_by_name.get(name)
        server_attr = server_attrs.get(name)
        if attr:
            card = (
                f"-「{i}」：项目名称：「{attr.name}」、"
                f"项目介绍：「{attr.description}」、"
                f"建议时长：「{attr.cost}」、"
                f"项目标签：「{attr.field}」、"
                f"景点照片：「图{photo_idx}是景点照片」"
            )
            images = (server_attr.images if server_attr else None) or attr.images
            if images:
                img_path = images[0].lstrip("/").replace("static/", "", 1)
                ref_image_paths.append(img_path)
                ref_image_descs.append(f"图{photo_idx}：{name} 景点照片")
                photo_idx += 1
        else:
            card = f"-「{i}」：「项目名称：{name}」"
        cards.append(card)
    stops_cards = "\n".join(cards)

    ref_image_descs.append(f"图{photo_idx}：尺木神奇世界地图")
    ref_images_desc = "\n".join(ref_image_descs)

    user_name = ""
    tour_type = ""
    for segment in addition_prompt.split(","):
        segment = segment.strip()
        if ":" in segment:
            key, val = segment.split(":", 1)
            key = key.strip().lower()
            val = val.strip()
            if any(k in key for k in ("昵称", "标题", "name")):
                user_name = val
            elif any(k in key for k in ("风格", "style", "type")):
                tour_type = val

    cfg_img = get_prompts()["postcard_image"]
    img_prompt = render_prompt(
        "postcard_image",
        route_info=tour_text,
        stops_summary=stops_summary,
        stops_cards=stops_cards,
        farewell=farewell,
        addition_prompt=addition_prompt,
        ref_images_desc=ref_images_desc,
        user_name=user_name,
        tour_type=tour_type,
    )

    await upload_text("data", f"{username}/postcard/image_prompt.txt", img_prompt)

    local_ref_images = ref_image_paths + ["map.jpg"]

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
        "local_ref_images": local_ref_images,
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

    input_images = []
    for local_path in task_data.get("local_ref_images", []):
        full_path = STATIC_DIR / local_path
        if full_path.exists():
            input_images.append(full_path.read_bytes())

    image_bytes_list = await generate_image(
        prompt=prompt, size=size, input_images=input_images or None,
    )

    filename = f"{uuid.uuid4().hex[:8]}.png"
    await upload_blob("data", f"{username}/postcard/{filename}", image_bytes_list[0], content_type="image/png")

    addition_prompt = task_data.get("addition_prompt", "")
    prompt_txt_name = filename.replace(".png", ".txt")
    await upload_text("data", f"{username}/postcard/{prompt_txt_name}", addition_prompt or "")

    image_url = f"/static/{username}/postcard/{filename}"

    return {"image_url": image_url}
