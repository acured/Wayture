from __future__ import annotations

import uuid
from datetime import datetime, timezone

from services.blob_storage import read_json, write_json
from services.queue_client import send_message


async def create_task(username: str, task_type: str, task_data: dict) -> str:
    task_id = uuid.uuid4().hex[:12]
    now = datetime.now(timezone.utc).isoformat()

    task_data["task_type"] = task_type
    task_data["username"] = username
    task_data["task_id"] = task_id
    await write_json("data", f"{username}/tasks/{task_id}/task.json", task_data)

    tasks = await read_json("data", f"{username}/tasks/tasks.json")
    tasks.append({
        "task_id": task_id,
        "task_type": task_type,
        "status": "pending",
        "created_at": now,
        "result": None,
    })
    await write_json("data", f"{username}/tasks/tasks.json", tasks)

    send_message({"task_id": task_id, "username": username})
    return task_id


async def update_task(username: str, task_id: str, status: str, result: dict | None = None) -> None:
    tasks = await read_json("data", f"{username}/tasks/tasks.json")
    for t in tasks:
        if t["task_id"] == task_id:
            t["status"] = status
            if result is not None:
                t["result"] = result
            break
    await write_json("data", f"{username}/tasks/tasks.json", tasks)


async def get_tasks(username: str) -> list[dict]:
    return await read_json("data", f"{username}/tasks/tasks.json")


async def get_task(username: str, task_id: str) -> dict | None:
    tasks = await read_json("data", f"{username}/tasks/tasks.json")
    for t in tasks:
        if t["task_id"] == task_id:
            return t
    return None
