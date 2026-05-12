from __future__ import annotations

import json
import uuid
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from models import (
    Attraction,
    GenerateGalleryRequest,
    GeneratePostcardRequest,
    GalleryResponse,
    MemoryMeta,
    PhotoMeta,
    PlanRouteRequest,
    PlanRouteResponse,
    PostcardResponse,
)
from services.config import get_map_meta
from services.gallery import generate_gallery_images
from services.postcard import generate_postcard
from services.route_planner import plan_route
from services.vision import classify_image

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
DATA_DIR = BASE_DIR / "data"

STATIC_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)

app = FastAPI(title="Wayture Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# ── helpers ──────────────────────────────────────────────────────

def _user_data_dir(username: str) -> Path:
    d = DATA_DIR / username
    d.mkdir(parents=True, exist_ok=True)
    return d


def _photo_meta_path(username: str) -> Path:
    return _user_data_dir(username) / "photos.json"


def _load_photos(username: str) -> list[dict]:
    p = _photo_meta_path(username)
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return []


def _save_photos(username: str, photos: list[dict]) -> None:
    p = _photo_meta_path(username)
    p.write_text(json.dumps(photos, ensure_ascii=False, indent=2), encoding="utf-8")


def _memories_path(username: str) -> Path:
    return _user_data_dir(username) / "memories.json"


def _load_memories(username: str) -> list[dict]:
    p = _memories_path(username)
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return []


def _save_memory(username: str, memory: dict) -> None:
    memories = _load_memories(username)
    memories.append(memory)
    p = _memories_path(username)
    p.write_text(json.dumps(memories, ensure_ascii=False, indent=2), encoding="utf-8")


# ── 0. 获取地图景点 meta ─────────────────────────────────────────

@app.get("/api/map-meta", response_model=list[Attraction])
async def api_get_map_meta():
    return get_map_meta()


# ── 1. 规划路线 ──────────────────────────────────────────────────

@app.post("/api/plan-route", response_model=PlanRouteResponse)
async def api_plan_route(req: PlanRouteRequest):
    return await plan_route(req.username, req.path_info)


# ── 2. 生成明信片 ────────────────────────────────────────────────

@app.post("/api/generate-postcard", response_model=PostcardResponse)
async def api_generate_postcard(req: GeneratePostcardRequest):
    return await generate_postcard(req.username, req.route_plan, req.attractions, req.addition_prompt)


# ── 3. 上传图片 ──────────────────────────────────────────────────

@app.post("/api/upload-image", response_model=PhotoMeta)
async def api_upload_image(
    file: UploadFile = File(...),
    username: str = Form(...),
    map_meta: str = Form(default=""),
):
    user_dir = STATIC_DIR / username
    user_dir.mkdir(parents=True, exist_ok=True)

    ext = Path(file.filename or "upload.jpg").suffix or ".jpg"
    safe_name = f"{uuid.uuid4().hex[:12]}{ext}"
    save_path = user_dir / safe_name

    content = await file.read()
    save_path.write_bytes(content)

    attractions = get_map_meta()
    if map_meta:
        try:
            attractions = [Attraction(**a) for a in json.loads(map_meta)]
        except Exception:
            pass

    try:
        classification = await classify_image(str(save_path), attractions)
    except Exception:
        classification = {"attraction_id": None, "attraction_name": "", "description": ""}

    photos = _load_photos(username)
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
        url=f"/static/{username}/{safe_name}",
        associated_location=classification.get("attraction_name") or None,
        associated_attraction=matched_attraction,
        description=classification.get("description", ""),
    )

    photos.append(meta.model_dump())
    _save_photos(username, photos)

    return meta


# ── 4. 获取图片 ──────────────────────────────────────────────────

@app.get("/api/images/{username}", response_model=list[PhotoMeta])
async def api_get_images(username: str):
    return _load_photos(username)


# ── 5. 生成图册（回忆） ──────────────────────────────────────────

@app.post("/api/generate-gallery", response_model=GalleryResponse)
async def api_generate_gallery(req: GenerateGalleryRequest):
    photos = _load_photos(req.username)
    if not photos:
        raise HTTPException(status_code=404, detail="该用户没有上传过照片")

    selected = [PhotoMeta(**p) for p in photos if p["index"] in req.selected_indices]
    if not selected:
        raise HTTPException(status_code=400, detail="未找到所选照片")

    memory = await generate_gallery_images(req.username, selected, str(STATIC_DIR))

    _save_memory(req.username, memory.model_dump())

    return GalleryResponse(username=req.username, memory=memory)


# ── 6. 获取所有回忆 ──────────────────────────────────────────────

@app.get("/api/memories/{username}", response_model=list[MemoryMeta])
async def api_get_memories(username: str):
    return _load_memories(username)


# ── 启动入口 ─────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
