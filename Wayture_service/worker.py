"""
Wayture Worker — 轮询 Azure Storage Queue 处理图片生成任务

运行: py worker.py
"""
from __future__ import annotations

import asyncio
import base64
import json
import time
import traceback
from datetime import datetime, timezone

from dotenv import load_dotenv

load_dotenv()

from services.blob_storage import read_json, write_json
from services.gallery import execute_album_task, execute_gallery_task, execute_journal_task
from services.postcard import execute_postcard_task
from services.queue_client import delete_message, receive_messages
from services.task_manager import update_task

EXECUTORS = {
    "postcard": execute_postcard_task,
    "gallery": execute_gallery_task,
    "album": execute_album_task,
    "journal": execute_journal_task,
}

MAX_ATTEMPTS = 3
RETRY_DELAY = 5

completed_count = 0
failed_count = 0


def log(task_id: str, status: str, desc: str):
    total = completed_count + failed_count
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{total}] [{task_id}] [{status}] {desc}  ({ts})")


async def _save_failure_log(task_id: str, username: str, task_type: str, task_data: dict, error: str, attempts: int):
    failure = {
        "task_id": task_id,
        "username": username,
        "task_type": task_type,
        "task_data": task_data,
        "error": error,
        "attempts": attempts,
        "failed_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        await write_json("task-logs", f"{task_id}.json", failure)
        log(task_id, "LOG", f"失败日志已保存到 task-logs/{task_id}.json")
    except Exception as e:
        log(task_id, "WARN", f"保存失败日志异常: {e}")


async def _save_memory_from_result(username: str, result: dict) -> None:
    memory = result.get("memory")
    if not memory:
        return
    memories = await read_json("data", f"{username}/memories/memories.json")
    memories.append(memory)
    await write_json("data", f"{username}/memories/memories.json", memories)


async def process_message(msg) -> None:
    global completed_count, failed_count

    task_id = "?"
    username = "?"
    task_type = "?"
    task_data = {}

    try:
        # ── 解码消息 ──
        try:
            raw = base64.b64decode(msg.content).decode("utf-8")
        except Exception as e:
            log("?", "ERROR", f"base64 解码失败: {e}")
            delete_message(msg)
            failed_count += 1
            return

        payload = json.loads(raw)
        task_id = payload["task_id"]
        username = payload["username"]

        # ── 读取任务数据 ──
        task_data = await read_json("data", f"{username}/tasks/{task_id}/task.json")
        if isinstance(task_data, list):
            log(task_id, "ERROR", "task.json 格式异常 (可能是旧任务)")
            await _save_failure_log(task_id, username, "unknown", {}, "task.json is a list, not dict", 0)
            await update_task(username, task_id, "failed", {"error": "task.json 格式异常"})
            delete_message(msg)
            failed_count += 1
            return

        task_type = task_data.get("task_type", "")
        log(task_id, "RECV", f"user={username} type={task_type}")

        executor = EXECUTORS.get(task_type)
        if not executor:
            log(task_id, "ERROR", f"未知任务类型: {task_type}")
            await _save_failure_log(task_id, username, task_type, task_data, f"未知任务类型: {task_type}", 0)
            await update_task(username, task_id, "failed", {"error": f"未知任务类型: {task_type}"})
            delete_message(msg)
            failed_count += 1
            return

        # ── 执行（含重试）──
        await update_task(username, task_id, "processing")

        last_error = ""
        for attempt in range(1, MAX_ATTEMPTS + 1):
            log(task_id, "PROCESSING", f"第 {attempt}/{MAX_ATTEMPTS} 次尝试 ({task_type})")
            start = time.time()
            try:
                result = await executor(username, task_data)
                break
            except Exception:
                elapsed = time.time() - start
                last_error = traceback.format_exc()
                log(task_id, "FAILED", f"第 {attempt}/{MAX_ATTEMPTS} 次失败 ({elapsed:.1f}s)")
                if attempt < MAX_ATTEMPTS:
                    log(task_id, f"RETRY {attempt}/{MAX_ATTEMPTS - 1}", f"{RETRY_DELAY}s 后重试...")
                    await asyncio.sleep(RETRY_DELAY)
        else:
            # 所有尝试都失败
            failed_count += 1
            log(task_id, "GIVE_UP", f"已重试 {MAX_ATTEMPTS} 次，放弃")
            await _save_failure_log(task_id, username, task_type, task_data, last_error[-1000:], MAX_ATTEMPTS)
            await update_task(username, task_id, "failed", {"error": last_error[-500:]})
            delete_message(msg)
            return

        # ── 成功 ──
        elapsed = time.time() - start

        if task_type in ("gallery", "album", "journal"):
            await _save_memory_from_result(username, result)

        await update_task(username, task_id, "completed", result)
        delete_message(msg)
        completed_count += 1
        log(task_id, "COMPLETED", f"user={username} type={task_type} ({elapsed:.1f}s)")

    except Exception:
        # 兜底：防止未捕获异常导致消息不被删除、worker 崩溃
        failed_count += 1
        log(task_id, "CRASH", f"未捕获异常")
        traceback.print_exc()
        try:
            await _save_failure_log(task_id, username, task_type, task_data, traceback.format_exc()[-1000:], 0)
            await update_task(username, task_id, "failed", {"error": "worker 未捕获异常"})
        except Exception:
            pass
        try:
            delete_message(msg)
        except Exception:
            pass


async def poll_loop():
    print("========================================")
    print("  Wayture Worker 启动")
    print(f"  队列: image-tasks  重试: {MAX_ATTEMPTS} 次")
    print("========================================")
    poll_count = 0
    while True:
        try:
            messages = list(receive_messages(max_messages=1, visibility_timeout=600))
        except Exception as e:
            print(f"[!] 拉取消息异常: {e}")
            traceback.print_exc()
            time.sleep(5)
            continue

        if not messages:
            poll_count += 1
            if poll_count % 50 == 0:
                ts = datetime.now().strftime("%H:%M:%S")
                print(f"[{completed_count + failed_count}] [--] [IDLE] 轮询 {poll_count} 次 (完成:{completed_count} 失败:{failed_count})  ({ts})")
            time.sleep(2)
            continue

        poll_count = 0
        for msg in messages:
            await process_message(msg)


if __name__ == "__main__":
    asyncio.run(poll_loop())
