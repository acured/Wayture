from __future__ import annotations

import math
import uuid
from datetime import datetime, timezone
from io import BytesIO

from PIL import Image

from models import AlbumPromptSpec, MemoryImageMeta, MemoryMeta, PhotoMeta
from services.ai import generate_image
from services.blob_storage import download_blob, upload_blob
from services.config import get_prompts, render_prompt


# ── prepare 函数（API 端调用，快速返回）──────────────────────────


def prepare_gallery(username: str, photos: list[PhotoMeta]) -> dict:
    cfg = get_prompts()["gallery_image"]
    sub_tasks = []
    for idx, photo in enumerate(photos, 1):
        attraction_name = photo.associated_attraction.get("name", "未知景点")
        description = photo.description or "一张旅行照片"
        prompt = render_prompt(
            "gallery_image",
            attraction_name=attraction_name,
            description=description,
        )
        blob_path = photo.url.lstrip("/").replace("static/", "", 1)
        sub_tasks.append({
            "prompt": prompt,
            "size": cfg.get("size", "1024x1024"),
            "ref_image": blob_path,
            "photo_meta": photo.model_dump(),
        })
    return {"sub_tasks": sub_tasks}


def prepare_album(username: str, prompt_specs: list[AlbumPromptSpec]) -> dict:
    sub_tasks = []
    for idx, spec in enumerate(prompt_specs, 1):
        blob_path = spec.photo.url.lstrip("/").replace("static/", "", 1)
        sub_tasks.append({
            "prompt": spec.prompt,
            "size": spec.size,
            "ref_image": blob_path,
            "photo_meta": spec.photo.model_dump(),
        })
    return {"sub_tasks": sub_tasks}


def prepare_journal(username: str, photos: list[PhotoMeta]) -> dict:
    cfg = get_prompts()["gallery_image"]
    prompt = render_prompt("gallery_image")
    ref_images = []
    photos_meta = []
    for photo in photos:
        blob_path = photo.url.lstrip("/").replace("static/", "", 1)
        ref_images.append(blob_path)
        photos_meta.append(photo.model_dump())
    return {
        "prompt": prompt,
        "size": cfg.get("size", "1024x1024"),
        "ref_images": ref_images,
        "photos_meta": photos_meta,
    }


# ── execute 函数（worker 端调用）─────────────────────────────────


async def execute_gallery_task(username: str, task_data: dict) -> dict:
    memory_id = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S") + "_" + uuid.uuid4().hex[:6]
    memory_images: list[MemoryImageMeta] = []

    for idx, sub in enumerate(task_data["sub_tasks"], 1):
        image_bytes_list = await generate_image(
            prompt=sub["prompt"],
            size=sub.get("size", "1024x1024"),
        )

        filename = f"album_{idx}_{uuid.uuid4().hex[:8]}.png"
        out_blob = f"{username}/album/{memory_id}/{filename}"
        await upload_blob("data", out_blob, image_bytes_list[0], content_type="image/png")

        photo = PhotoMeta(**sub["photo_meta"])
        attraction_name = photo.associated_attraction.get("name", "未知景点")
        description = photo.description or "一张旅行照片"

        memory_images.append(MemoryImageMeta(
            index=idx,
            source_photo=photo,
            generated_url=f"/static/{username}/album/{memory_id}/{filename}",
            description=f"{attraction_name} - {description}",
        ))

    spot_names = []
    for img in memory_images:
        name = img.source_photo.associated_attraction.get("name", "")
        if name and name not in spot_names:
            spot_names.append(name)
    title = "、".join(spot_names) + " 回忆录" if spot_names else "旅行回忆录"

    memory = MemoryMeta(
        id=memory_id,
        username=username,
        created_at=datetime.now(timezone.utc).isoformat(),
        title=title,
        images=memory_images,
        source_photo_count=len(task_data["sub_tasks"]),
        generated_image_count=len(memory_images),
    )
    return {"memory": memory.model_dump()}


async def execute_album_task(username: str, task_data: dict) -> dict:
    return await execute_gallery_task(username, task_data)


async def execute_journal_task(username: str, task_data: dict) -> dict:
    memory_id = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S") + "_" + uuid.uuid4().hex[:6]

    image_bytes_list = await generate_image(
        prompt=task_data["prompt"],
        size=task_data.get("size", "1024x1024"),
    )

    filename = f"journal_{uuid.uuid4().hex[:8]}.png"
    out_blob = f"{username}/journal/{memory_id}/{filename}"
    await upload_blob("data", out_blob, image_bytes_list[0], content_type="image/png")

    generated_url = f"/static/{username}/journal/{memory_id}/{filename}"

    photos_meta = task_data.get("photos_meta", [])
    spot_names = []
    for pm in photos_meta:
        name = pm.get("associated_attraction", {}).get("name", "")
        if name and name not in spot_names:
            spot_names.append(name)
    title = "、".join(spot_names) + " 手账" if spot_names else "旅行手账"

    first_photo = PhotoMeta(**photos_meta[0]) if photos_meta else PhotoMeta(
        index=0, filename="", url="",
    )

    memory_images = [MemoryImageMeta(
        index=1,
        source_photo=first_photo,
        generated_url=generated_url,
        description=title,
    )]

    memory = MemoryMeta(
        id=memory_id,
        username=username,
        created_at=datetime.now(timezone.utc).isoformat(),
        title=title,
        images=memory_images,
        source_photo_count=len(photos_meta),
        generated_image_count=1,
    )
    return {"memory": memory.model_dump()}


# ── get_album_prompts（保持不变）─────────────────────────────────


def get_album_prompts(photos: list[PhotoMeta]) -> list[AlbumPromptSpec]:
    cfg = get_prompts()
    album_keys = sorted(k for k in cfg if k.startswith("album_"))

    if not album_keys:
        raise ValueError("No album prompt templates configured (need keys starting with 'album_' in prompts.json)")

    specs: list[AlbumPromptSpec] = []
    for i, photo in enumerate(photos):
        key = album_keys[i % len(album_keys)]
        template_cfg = cfg[key]

        prompt = render_prompt(
            key,
            attraction_name=photo.associated_attraction.get("name", "未知景点"),
            description=photo.description or "一张旅行照片",
        )

        specs.append(AlbumPromptSpec(
            prompt_name=key,
            prompt=prompt,
            photo=photo,
            size=template_cfg.get("size", "1024x1024"),
        ))

    return specs


# ── _compose_photos（保持不变）───────────────────────────────────


def _compose_photos(photo_bytes_list: list[bytes], max_size: int = 2048) -> bytes:
    images = [Image.open(BytesIO(b)).convert("RGB") for b in photo_bytes_list]
    n = len(images)
    cols = math.ceil(math.sqrt(n))
    rows = math.ceil(n / cols)

    cell_w = max_size // cols
    cell_h = max_size // rows

    canvas = Image.new("RGB", (cols * cell_w, rows * cell_h), (255, 255, 255))
    for i, img in enumerate(images):
        img.thumbnail((cell_w, cell_h), Image.LANCZOS)
        x = (i % cols) * cell_w + (cell_w - img.width) // 2
        y = (i // cols) * cell_h + (cell_h - img.height) // 2
        canvas.paste(img, (x, y))

    buf = BytesIO()
    canvas.save(buf, format="PNG")
    return buf.getvalue()
