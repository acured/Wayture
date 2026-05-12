from __future__ import annotations

import base64
import os
import uuid
from datetime import datetime, timezone

from models import MemoryImageMeta, MemoryMeta, PhotoMeta
from services.azure_client import get_postcard_client
from services.config import get_prompts, render_prompt


async def generate_gallery_images(
    username: str,
    photos: list[PhotoMeta],
    static_dir: str,
) -> MemoryMeta:
    memory_id = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S") + "_" + uuid.uuid4().hex[:6]
    gallery_dir = os.path.join(static_dir, username, "gallery", memory_id)
    os.makedirs(gallery_dir, exist_ok=True)

    client, deployment = get_postcard_client()
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

        resp = await client.images.generate(
            model=deployment,
            prompt=prompt,
            size=cfg.get("size", "1024x1024"),
            n=1,
        )

        image_data = resp.data[0]
        filename = f"gallery_{idx}_{uuid.uuid4().hex[:8]}.png"
        filepath = os.path.join(gallery_dir, filename)

        if hasattr(image_data, "b64_json") and image_data.b64_json:
            with open(filepath, "wb") as f:
                f.write(base64.b64decode(image_data.b64_json))
        elif hasattr(image_data, "url") and image_data.url:
            import httpx
            async with httpx.AsyncClient() as http:
                img_resp = await http.get(image_data.url)
                with open(filepath, "wb") as f:
                    f.write(img_resp.content)

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
