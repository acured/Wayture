from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path

from services.ai import generate_image
from services.azure_client import get_image_client
from services.blob_storage import download_blob, upload_blob, upload_text

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


async def execute_postcard_task(username, task_data):
    client, deployment = get_image_client()
    prompt = task_data["prompt"]
    size = task_data.get("size", "1024x1024")

    input_images = []
    for local_path in task_data.get("local_ref_images", []):
        full_path = STATIC_DIR / local_path
        if full_path.exists():
            input_images.append(full_path.read_bytes())

    image_bytes_list = generate_image(
        client, deployment, prompt, size=size, input_images=input_images or None,
    )

    filename = f"{uuid.uuid4().hex[:8]}.png"
    await upload_blob("data", f"{username}/postcard/{filename}", image_bytes_list[0], content_type="image/png")

    addition_prompt = task_data.get("addition_prompt", "")
    prompt_txt_name = filename.replace(".png", ".txt")
    await upload_text("data", f"{username}/postcard/{prompt_txt_name}", addition_prompt or "")

    return {"image_url": f"/static/{username}/postcard/{filename}"}


async def execute_gallery_task(username, task_data):
    client, deployment = get_image_client()
    memory_id = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S") + "_" + uuid.uuid4().hex[:6]
    memory_images = []

    for idx, sub in enumerate(task_data["sub_tasks"], 1):
        image_bytes_list = generate_image(
            client, deployment, sub["prompt"], size=sub.get("size", "1024x1024"),
        )

        filename = f"album_{idx}_{uuid.uuid4().hex[:8]}.png"
        out_blob = f"{username}/album/{memory_id}/{filename}"
        await upload_blob("data", out_blob, image_bytes_list[0], content_type="image/png")

        photo_meta = sub["photo_meta"]
        attraction_name = photo_meta.get("associated_attraction", {}).get("name", "旅行景点")
        description = photo_meta.get("description") or "一张旅行照片"

        memory_images.append({
            "index": idx,
            "source_photo": photo_meta,
            "generated_url": f"/static/{username}/album/{memory_id}/{filename}",
            "description": f"{attraction_name} - {description}",
        })

    spot_names = []
    for img in memory_images:
        name = img["source_photo"].get("associated_attraction", {}).get("name", "")
        if name and name not in spot_names:
            spot_names.append(name)
    title = "、".join(spot_names) + " 回忆录" if spot_names else "旅行回忆录"

    memory = {
        "id": memory_id,
        "username": username,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "title": title,
        "type": "album",
        "images": memory_images,
        "source_photo_count": len(task_data["sub_tasks"]),
        "generated_image_count": len(memory_images),
    }
    return {"memory": memory}


async def execute_album_task(username, task_data):
    return await execute_gallery_task(username, task_data)


async def execute_journal_task(username, task_data):
    client, deployment = get_image_client()
    memory_id = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S") + "_" + uuid.uuid4().hex[:6]

    input_images = []
    for blob_path in task_data.get("ref_images", []):
        try:
            img_bytes = await download_blob("data", blob_path)
            input_images.append(img_bytes)
        except Exception:
            pass

    image_bytes_list = generate_image(
        client, deployment, task_data["prompt"],
        size=task_data.get("size", "1024x1024"),
        input_images=input_images or None,
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

    first_photo = photos_meta[0] if photos_meta else {"index": 0, "filename": "", "url": ""}

    memory = {
        "id": memory_id,
        "username": username,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "title": title,
        "type": "journal",
        "images": [{
            "index": 1,
            "source_photo": first_photo,
            "generated_url": generated_url,
            "description": title,
        }],
        "source_photo_count": len(photos_meta),
        "generated_image_count": 1,
    }
    return {"memory": memory}
