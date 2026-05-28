from __future__ import annotations

from typing import Any, Optional
from pydantic import BaseModel, Field


# ── 景点 / 地图节点 ──────────────────────────────────────────────

class Position(BaseModel):
    top: str
    left: str


class Attraction(BaseModel):
    id: int
    location: list[float] = Field(..., description="[x, y] 坐标")
    name: str
    description: str
    field: str = ""
    cost: str = ""
    images: list[str] = []
    position: Optional[Position] = None
    color: Optional[str] = None


# ── 1. 规划路线 ──────────────────────────────────────────────────

class PlanRouteRequest(BaseModel):
    username: str
    path_info: list[Attraction]


class PlannedStop(BaseModel):
    order: int
    attraction: Attraction
    tips: str = ""


class PlanRouteResponse(BaseModel):
    username: str
    total_time: str
    route: list[PlannedStop]
    summary: str


# ── 2. 生成明信片 ────────────────────────────────────────────────

class GeneratePostcardRequest(BaseModel):
    username: str
    route_plan: list[PlannedStop]
    attractions: list[Attraction]
    addition_prompt: str = ""


class PostcardResponse(BaseModel):
    username: str
    title: str
    greeting: str
    stops: list[dict[str, Any]]
    farewell: str
    image_url: str = ""


# ── 3. 上传图片 ──────────────────────────────────────────────────

class PhotoMeta(BaseModel):
    index: int
    filename: str
    url: str
    associated_location: Optional[str] = None
    associated_attraction: dict[str, Any] = {}
    description: str = ""


# ── 4. 获取图片 ──────────────────────────────────────────────────
# 返回 list[PhotoMeta]，无需额外模型


# ── 5. 生成图册（回忆） ──────────────────────────────────────────

class GenerateGalleryRequest(BaseModel):
    username: str
    selected_indices: list[int]


class MemoryImageMeta(BaseModel):
    index: int
    source_photo: PhotoMeta
    generated_url: str
    description: str = ""


class MemoryMeta(BaseModel):
    id: str
    username: str
    created_at: str
    title: str = ""
    type: str = ""
    images: list[MemoryImageMeta] = []
    source_photo_count: int = 0
    generated_image_count: int = 0
    task_id: Optional[str] = None
    status: str = "completed"


class GalleryResponse(BaseModel):
    username: str
    memory: MemoryMeta


# ── 7. 生成相册（差异化 prompt） ─────────────────────────────────

class AlbumPromptSpec(BaseModel):
    prompt_name: str
    prompt: str
    photo: PhotoMeta
    size: str = "1024x1024"


class GenerateAlbumRequest(BaseModel):
    username: str
    selected_indices: list[int]


# ── 8. 生成手账（多图合一） ──────────────────────────────────────

class GenerateJournalRequest(BaseModel):
    username: str
    selected_indices: list[int]
    addition_prompt: str = ""


# ── 9. 异步图片任务 ─────────────────────────────────────────────

class ImageTaskResponse(BaseModel):
    task_id: str
    username: str
    task_type: str
    status: str


class TaskMeta(BaseModel):
    task_id: str
    task_type: str
    status: str
    created_at: str
    result: Optional[dict[str, Any]] = None
