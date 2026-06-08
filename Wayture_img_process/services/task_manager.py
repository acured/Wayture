from __future__ import annotations

from services.blob_storage import read_json, write_json


async def update_task(username, task_id, status, result=None):
    tasks = await read_json("data", f"{username}/tasks/tasks.json")
    for t in tasks:
        if t["task_id"] == task_id:
            t["status"] = status
            if result is not None:
                t["result"] = result
            break
    await write_json("data", f"{username}/tasks/tasks.json", tasks)
