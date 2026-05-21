from __future__ import annotations

import json
import mimetypes
import uuid
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response

from models import (
    Attraction,
    GenerateAlbumRequest,
    GenerateGalleryRequest,
    GenerateJournalRequest,
    GeneratePostcardRequest,
    ImageTaskResponse,
    MemoryMeta,
    PhotoMeta,
    PlanRouteRequest,
    PlanRouteResponse,
    PostcardResponse,
    TaskMeta,
)
from services.blob_storage import download_blob, read_json, upload_blob, write_json
from services.config import get_map_meta
from services.gallery import get_album_prompts, prepare_album, prepare_gallery, prepare_journal
from services.postcard import prepare_postcard
from services.route_planner import plan_route
from services.task_manager import create_task, get_task, get_tasks
from services.vision import classify_image

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(title="Wayture Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── static file proxy ──────────────────────────────────────────

LOCAL_STATIC_PREFIXES = ("map_data/",)
LOCAL_STATIC_FILES = {"map.jpg"}


@app.get("/static/{path:path}")
async def serve_static(path: str):
    is_local = path in LOCAL_STATIC_FILES or any(path.startswith(p) for p in LOCAL_STATIC_PREFIXES)
    if is_local:
        local = STATIC_DIR / path
        if local.exists():
            return FileResponse(local)
        raise HTTPException(status_code=404, detail="File not found")

    try:
        data = await download_blob("data", path)
    except Exception:
        raise HTTPException(status_code=404, detail="File not found")

    media_type = mimetypes.guess_type(path)[0] or "application/octet-stream"
    return Response(content=data, media_type=media_type)


# ── helpers ──────────────────────────────────────────────────────

async def _load_photos(username: str) -> list[dict]:
    return await read_json("data", f"{username}/photos/photos.json")


async def _save_photos(username: str, photos: list[dict]) -> None:
    await write_json("data", f"{username}/photos/photos.json", photos)


async def _load_memories(username: str) -> list[dict]:
    return await read_json("data", f"{username}/memories/memories.json")


async def _save_memory(username: str, memory: dict) -> None:
    memories = await _load_memories(username)
    memories.append(memory)
    await write_json("data", f"{username}/memories/memories.json", memories)


# ── 0. 获取地图景点 meta ─────────────────────────────────────────

@app.get("/api/map-meta", response_model=list[Attraction])
async def api_get_map_meta():
    return get_map_meta()


# ── 1. 规划路线 ──────────────────────────────────────────────────

@app.post("/api/plan-route", response_model=PlanRouteResponse)
async def api_plan_route(req: PlanRouteRequest):
    return await plan_route(req.username, req.path_info)


# ── 2. 生成明信片（异步：chat 同步 + 图片入队）────────────────────

@app.post("/api/generate-postcard")
async def api_generate_postcard(req: GeneratePostcardRequest):
    response, task_data = await prepare_postcard(
        req.username, req.route_plan, req.attractions, req.addition_prompt,
    )
    task_id = await create_task(req.username, "postcard", task_data)

    return {
        **response.model_dump(),
        "image_task_id": task_id,
    }


# ── 3. 上传图片 ──────────────────────────────────────────────────

@app.post("/api/upload-image", response_model=PhotoMeta)
async def api_upload_image(
    file: UploadFile = File(...),
    username: str = Form(...),
    map_meta: str = Form(default=""),
):
    ext = Path(file.filename or "upload.jpg").suffix or ".jpg"
    safe_name = f"{uuid.uuid4().hex[:12]}{ext}"

    content = await file.read()
    await upload_blob("data", f"{username}/photos/{safe_name}", content, content_type=file.content_type)

    attractions = get_map_meta()
    if map_meta:
        try:
            attractions = [Attraction(**a) for a in json.loads(map_meta)]
        except Exception:
            pass

    try:
        classification = await classify_image(content, ext, attractions)
    except Exception:
        classification = {"attraction_id": None, "attraction_name": "", "description": ""}

    photos = await _load_photos(username)
    next_index = max((p["index"] for p in photos), default=0) + 1

    matched_attraction = {}
    aid = classification.get("attraction_id")
    if aid is not None:
        for a in attractions:
            if a.id == aid:
                matched_attraction = a.model_dump()
                break

    meta = PhotoMeta(
        index=next_index,
        filename=safe_name,
        url=f"/static/{username}/photos/{safe_name}",
        associated_location=classification.get("attraction_name") or None,
        associated_attraction=matched_attraction,
        description=classification.get("description", ""),
    )

    photos.append(meta.model_dump())
    await _save_photos(username, photos)

    return meta


# ── 4. 获取图片 ──────────────────────────────────────────────────

@app.get("/api/images/{username}", response_model=list[PhotoMeta])
async def api_get_images(username: str):
    return await _load_photos(username)


# ── 5. 生成图册（异步入队）────────────────────────────────────────

@app.post("/api/generate-gallery", response_model=ImageTaskResponse)
async def api_generate_gallery(req: GenerateGalleryRequest):
    photos = await _load_photos(req.username)
    if not photos:
        raise HTTPException(status_code=404, detail="该用户没有上传过照片")

    selected = [PhotoMeta(**p) for p in photos if p["index"] in req.selected_indices]
    if not selected:
        raise HTTPException(status_code=400, detail="未找到所选照片")

    task_data = prepare_gallery(req.username, selected)
    task_id = await create_task(req.username, "gallery", task_data)

    return ImageTaskResponse(
        task_id=task_id, username=req.username, task_type="gallery", status="pending",
    )


# ── 6. 生成相册（异步入队）────────────────────────────────────────

@app.post("/api/generate-album", response_model=ImageTaskResponse)
async def api_generate_album(req: GenerateAlbumRequest):
    photos = await _load_photos(req.username)
    if not photos:
        raise HTTPException(status_code=404, detail="该用户没有上传过照片")

    selected = [PhotoMeta(**p) for p in photos if p["index"] in req.selected_indices]
    if not selected:
        raise HTTPException(status_code=400, detail="未找到所选照片")

    prompt_specs = get_album_prompts(selected)
    task_data = prepare_album(req.username, prompt_specs)
    task_id = await create_task(req.username, "album", task_data)

    return ImageTaskResponse(
        task_id=task_id, username=req.username, task_type="album", status="pending",
    )


# ── 7. 生成手账（异步入队）────────────────────────────────────────

@app.post("/api/generate-journal", response_model=ImageTaskResponse)
async def api_generate_journal(req: GenerateJournalRequest):
    photos = await _load_photos(req.username)
    if not photos:
        raise HTTPException(status_code=404, detail="该用户没有上传过照片")

    selected = [PhotoMeta(**p) for p in photos if p["index"] in req.selected_indices]
    if not selected:
        raise HTTPException(status_code=400, detail="未找到所选照片")

    task_data = prepare_journal(req.username, selected)
    task_id = await create_task(req.username, "journal", task_data)

    return ImageTaskResponse(
        task_id=task_id, username=req.username, task_type="journal", status="pending",
    )


# ── 8. 获取所有回忆 ──────────────────────────────────────────────

@app.get("/api/memories/{username}", response_model=list[MemoryMeta])
async def api_get_memories(username: str):
    return await _load_memories(username)


# ── 9. 任务查询 ──────────────────────────────────────────────────

@app.get("/api/tasks/{username}", response_model=list[TaskMeta])
async def api_get_tasks(username: str):
    return await get_tasks(username)


@app.get("/api/tasks/{username}/{task_id}", response_model=TaskMeta)
async def api_get_task(username: str, task_id: str):
    task = await get_task(username, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    return task


# ── 启动入口 ─────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
