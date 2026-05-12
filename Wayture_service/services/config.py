from __future__ import annotations

import json
from pathlib import Path

from models import Attraction

_CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"

_prompts: dict | None = None
_prompt_templates: dict[str, str] = {}
_map_meta: list[Attraction] | None = None


def get_prompts() -> dict:
    global _prompts
    if _prompts is None:
        p = _CONFIG_DIR / "prompts.json"
        _prompts = json.loads(p.read_text(encoding="utf-8"))
    return _prompts


def get_prompt_template(name: str) -> str:
    if name not in _prompt_templates:
        cfg = get_prompts()[name]
        md_path = _CONFIG_DIR / cfg["prompt_file"]
        _prompt_templates[name] = md_path.read_text(encoding="utf-8").strip()
    return _prompt_templates[name]


def render_prompt(name: str, **kwargs: str) -> str:
    template = get_prompt_template(name)
    for key, value in kwargs.items():
        template = template.replace("{{" + key + "}}", value)
    return template


def get_map_meta() -> list[Attraction]:
    global _map_meta
    if _map_meta is None:
        p = _CONFIG_DIR / "map_meta.json"
        raw = json.loads(p.read_text(encoding="utf-8"))
        _map_meta = [Attraction(**item) for item in raw]
    return _map_meta
