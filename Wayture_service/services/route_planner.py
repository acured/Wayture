from __future__ import annotations

import json

from models import Attraction, PlannedStop, PlanRouteResponse
from services.ai import chat_completion
from services.config import get_prompts, render_prompt


async def plan_route(username: str, attractions: list[Attraction]) -> PlanRouteResponse:
    spots = [
        {
            "id": a.id,
            "name": a.name,
            "description": a.description,
            "field": a.field,
            "cost": a.cost,
            "location": a.location,
        }
        for a in attractions
    ]

    cfg = get_prompts()["route_planner"]
    prompt = render_prompt(
        "route_planner",
        spots=json.dumps(spots, ensure_ascii=False),
    )

    try:
        raw = await chat_completion(
            messages=[{"role": "user", "content": prompt}],
            temperature=cfg.get("temperature", 0.7),
        )
        data = json.loads(raw)
    except Exception:
        data = {
            "route": [{"id": a.id, "order": i, "tips": ""} for i, a in enumerate(attractions, 1)],
            "total_time": "",
            "summary": "按选择顺序游览",
        }

    attraction_map = {a.id: a for a in attractions}
    planned: list[PlannedStop] = []
    for item in data["route"]:
        att = attraction_map.get(item["id"])
        if att:
            planned.append(PlannedStop(order=item["order"], attraction=att, tips=item.get("tips", "")))

    return PlanRouteResponse(
        username=username,
        total_time=data.get("total_time", ""),
        route=planned,
        summary=data.get("summary", ""),
    )
