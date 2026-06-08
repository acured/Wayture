from __future__ import annotations

import base64
import json
import random

from models import Attraction
from services.ai import chat_completion
from services.config import get_map_meta, get_prompts, render_prompt

from pathlib import Path

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
REF_GRID_PATH = STATIC_DIR / "ref_grid.jpg"

_ref_grid_b64: str | None = None


def _get_ref_grid_b64() -> str:
    global _ref_grid_b64
    if _ref_grid_b64 is not None:
        return _ref_grid_b64
    if REF_GRID_PATH.exists():
        _ref_grid_b64 = base64.b64encode(REF_GRID_PATH.read_bytes()).decode()
    else:
        _ref_grid_b64 = ""
    return _ref_grid_b64


async def classify_image(
    image_data: bytes,
    image_ext: str,
    map_meta: list[Attraction],
) -> dict:
    b64 = base64.b64encode(image_data).decode()

    ext = image_ext.lower().lstrip(".")
    mime_map = {"jpg": "jpeg", "jpeg": "jpeg", "png": "png", "gif": "gif", "webp": "webp"}
    mime = mime_map.get(ext, "jpeg")

    spots = [
        {"id": a.id, "name": a.name, "description": a.description, "field": a.field}
        for a in map_meta
    ]

    cfg = get_prompts()["vision_classify"]
    prompt = render_prompt(
        "vision_classify",
        spots=json.dumps(spots, ensure_ascii=False),
    )

    content: list[dict] = [{"type": "text", "text": prompt}]

    ref_grid = _get_ref_grid_b64()
    if ref_grid:
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{ref_grid}"},
        })

    content.append({
        "type": "image_url",
        "image_url": {"url": f"data:image/{mime};base64,{b64}"},
    })

    try:
        raw = await chat_completion(
            messages=[{"role": "user", "content": content}],
            temperature=cfg.get("temperature", 0.3),
        )
        return json.loads(raw)
    except Exception:
        fallback = random.choice(map_meta) if map_meta else None
        return {
            "attraction_id": fallback.id if fallback else None,
            "attraction_name": fallback.name if fallback else "",
            "description": "",
        }
