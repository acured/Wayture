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


async def generate_gallery_images(
    username: str,
    photos: list[PhotoMeta],
) -> MemoryMeta:
    memory_id = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S") + "_" + uuid.uuid4().hex[:6]

    cfg = get_prompts()["gallery_image"]
    memory_images: list[MemoryImageMeta] = []

    for idx, photo in enumerate(photos, 1):
        attraction_name = photo.associated_attraction.get("name", "未知景点")
        description = photo.description or "一张旅行照片"

        prompt = render_prompt(
            "gallery_image",
            attraction_name=attraction_name,
            description=description,
        )

        blob_path = photo.url.lstrip("/").replace("static/", "", 1)
        source_bytes = await download_blob("data", blob_path)

        image_bytes_list = await generate_image(
            prompt=prompt,
            size=cfg.get("size", "1024x1024"),
            input_images=[source_bytes],
        )

        filename = f"gallery_{idx}_{uuid.uuid4().hex[:8]}.png"
        out_blob = f"{username}/gallery/{memory_id}/{filename}"
        await upload_blob("data", out_blob, image_bytes_list[0], content_type="image/png")

        generated_url = f"/static/{username}/gallery/{memory_id}/{filename}"

        memory_images.append(MemoryImageMeta(
            index=idx,
            source_photo=photo,
            generated_url=generated_url,
            description=f"{attraction_name} - {description}",
        ))

    spot_names = []
    for img in memory_images:
        name = img.source_photo.associated_attraction.get("name", "")
        if name and name not in spot_names:
            spot_names.append(name)
    title = "、".join(spot_names) + " 回忆录" if spot_names else "旅行回忆录"

    return MemoryMeta(
        id=memory_id,
        username=username,
        created_at=datetime.now(timezone.utc).isoformat(),
        title=title,
        images=memory_images,
        source_photo_count=len(photos),
        generated_image_count=len(memory_images),
    )


# ── 差异化 prompt 相册生成 ───────────────────────────────────────


def get_album_prompts(photos: list[PhotoMeta]) -> list[AlbumPromptSpec]:
    """返回相册生成的 prompt 列表，每个 spec 包含 prompt 文本和对应的用户照片。

    从 prompts.json 中加载所有以 "album_" 开头的模板，按 key 排序后
    以 round-robin 方式分配给用户选择的照片。

    自定义方式:
    - 在 config/prompts.json 中增减 album_ 开头的条目
    - 修改此函数中的分配逻辑（如按景点类型匹配不同风格）
    """
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


async def generate_album_images(
    username: str,
    prompt_specs: list[AlbumPromptSpec],
) -> MemoryMeta:
    """根据 prompt specs 列表逐张生成相册图片。"""
    memory_id = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S") + "_" + uuid.uuid4().hex[:6]

    memory_images: list[MemoryImageMeta] = []

    for idx, spec in enumerate(prompt_specs, 1):
        photo = spec.photo
        blob_path = photo.url.lstrip("/").replace("static/", "", 1)
        source_bytes = await download_blob("data", blob_path)

        image_bytes_list = await generate_image(
            prompt=spec.prompt,
            size=spec.size,
            input_images=[source_bytes],
        )

        filename = f"gallery_{idx}_{uuid.uuid4().hex[:8]}.png"
        out_blob = f"{username}/gallery/{memory_id}/{filename}"
        await upload_blob("data", out_blob, image_bytes_list[0], content_type="image/png")

        generated_url = f"/static/{username}/gallery/{memory_id}/{filename}"
        attraction_name = photo.associated_attraction.get("name", "未知景点")
        description = photo.description or "一张旅行照片"

        memory_images.append(MemoryImageMeta(
            index=idx,
            source_photo=photo,
            generated_url=generated_url,
            description=f"{attraction_name} - {description}",
        ))

    spot_names = []
    for img in memory_images:
        name = img.source_photo.associated_attraction.get("name", "")
        if name and name not in spot_names:
            spot_names.append(name)
    title = "、".join(spot_names) + " 回忆录" if spot_names else "旅行回忆录"

    return MemoryMeta(
        id=memory_id,
        username=username,
        created_at=datetime.now(timezone.utc).isoformat(),
        title=title,
        images=memory_images,
        source_photo_count=len(prompt_specs),
        generated_image_count=len(memory_images),
    )


# ── 手账生成（多图合一） ────────────────────────────────────────


def _compose_photos(photo_bytes_list: list[bytes], max_size: int = 2048) -> bytes:
    """将多张照片拼成一张网格合成图。"""
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


async def generate_journal_image(
    username: str,
    photos: list[PhotoMeta],
) -> MemoryMeta:
    """将所有选中照片拼成一张合成图，再生成一张手账图片。"""
    memory_id = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S") + "_" + uuid.uuid4().hex[:6]

    cfg = get_prompts()["gallery_image"]
    prompt = render_prompt("gallery_image")

    all_bytes: list[bytes] = []
    for photo in photos:
        blob_path = photo.url.lstrip("/").replace("static/", "", 1)
        all_bytes.append(await download_blob("data", blob_path))

    composite = _compose_photos(all_bytes)

    image_bytes_list = await generate_image(
        prompt=prompt,
        size=cfg.get("size", "1024x1024"),
        input_images=[composite],
    )

    filename = f"journal_{uuid.uuid4().hex[:8]}.png"
    out_blob = f"{username}/gallery/{memory_id}/{filename}"
    await upload_blob("data", out_blob, image_bytes_list[0], content_type="image/png")

    generated_url = f"/static/{username}/gallery/{memory_id}/{filename}"

    spot_names = []
    for photo in photos:
        name = photo.associated_attraction.get("name", "")
        if name and name not in spot_names:
            spot_names.append(name)
    title = "、".join(spot_names) + " 手账" if spot_names else "旅行手账"

    memory_images = [MemoryImageMeta(
        index=1,
        source_photo=photos[0],
        generated_url=generated_url,
        description=title,
    )]

    return MemoryMeta(
        id=memory_id,
        username=username,
        created_at=datetime.now(timezone.utc).isoformat(),
        title=title,
        images=memory_images,
        source_photo_count=len(photos),
        generated_image_count=1,
    )
