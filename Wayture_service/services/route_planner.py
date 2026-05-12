from __future__ import annotations

import json

from models import Attraction, PlannedStop, PlanRouteResponse
from services.azure_client import get_vision_client
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

    client, deployment = get_vision_client()
    resp = await client.chat.completions.create(
        model=deployment,
        messages=[{"role": "user", "content": prompt}],
        temperature=cfg.get("temperature", 0.7),
    )

    raw = resp.choices[0].message.content.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()

    data = json.loads(raw)

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
