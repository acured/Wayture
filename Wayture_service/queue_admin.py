"""
Wayture Queue 管理工具 — 查看/删除/添加队列任务

运行: py operator.py
"""
from __future__ import annotations

import base64
import json
import os

from dotenv import load_dotenv

load_dotenv()

from azure.storage.queue import QueueClient

QUEUE_NAME = "image-tasks"


def _get_client() -> QueueClient:
    account = os.environ["AZURE_STORAGE_ACCOUNT"]
    sas = os.environ["AZURE_STORAGE_SAS_TOKEN"]
    return QueueClient(
        account_url=f"https://{account}.queue.core.windows.net?{sas}",
        queue_name=QUEUE_NAME,
    )


def _decode(content: str) -> dict:
    try:
        raw = base64.b64decode(content).decode("utf-8")
        return json.loads(raw)
    except Exception:
        return {"_raw": content}


def cmd_list(client: QueueClient):
    props = client.get_queue_properties()
    count = props.approximate_message_count
    print(f"\n队列消息数 (约): {count}")

    if count == 0:
        print("队列为空")
        return

    messages = list(client.peek_messages(max_messages=min(count, 32)))
    if not messages:
        print("没有可查看的消息")
        return

    print(f"\n{'序号':<4} {'message_id':<40} {'username':<15} {'task_type':<12} {'task_id'}")
    print("-" * 110)
    for i, msg in enumerate(messages, 1):
        payload = _decode(msg.content)
        username = payload.get("username", "?")
        task_id = payload.get("task_id", "?")
        task_type = payload.get("task_type", "-")
        print(f"{i:<4} {msg.id:<40} {username:<15} {task_type:<12} {task_id}")


def cmd_delete(client: QueueClient):
    messages = list(client.receive_messages(max_messages=32, visibility_timeout=30))
    if not messages:
        print("\n队列为空，没有可删除的消息")
        return

    print(f"\n当前队列中有 {len(messages)} 条消息:")
    for i, msg in enumerate(messages, 1):
        payload = _decode(msg.content)
        print(f"  {i}. [{payload.get('username','?')}] task_id={payload.get('task_id','?')}")

    choice = input("\n输入序号删除 (多个用逗号分隔, 'all' 删全部, 回车取消): ").strip()
    if not choice:
        print("已取消")
        return

    if choice.lower() == "all":
        for msg in messages:
            client.delete_message(msg)
        print(f"已删除全部 {len(messages)} 条消息")
        return

    try:
        indices = [int(x.strip()) for x in choice.split(",")]
    except ValueError:
        print("输入无效")
        return

    deleted = 0
    for idx in indices:
        if 1 <= idx <= len(messages):
            client.delete_message(messages[idx - 1])
            deleted += 1
            payload = _decode(messages[idx - 1].content)
            print(f"  已删除: task_id={payload.get('task_id','?')}")
        else:
            print(f"  序号 {idx} 超出范围，跳过")
    print(f"共删除 {deleted} 条")


def cmd_add(client: QueueClient):
    username = input("\n用户名 (默认 demo_user): ").strip() or "demo_user"
    task_id = input("任务 ID: ").strip()
    if not task_id:
        print("任务 ID 不能为空")
        return

    msg = {"task_id": task_id, "username": username}
    encoded = base64.b64encode(json.dumps(msg, ensure_ascii=False).encode("utf-8")).decode("utf-8")
    client.send_message(encoded)
    print(f"已发送: {json.dumps(msg, ensure_ascii=False)}")


def cmd_clear(client: QueueClient):
    confirm = input("\n确认清空队列所有消息? (yes/no): ").strip()
    if confirm.lower() == "yes":
        client.clear_messages()
        print("队列已清空")
    else:
        print("已取消")


def cmd_stats(client: QueueClient):
    props = client.get_queue_properties()
    print(f"\n队列名称: {QUEUE_NAME}")
    print(f"消息数 (约): {props.approximate_message_count}")


def main():
    client = _get_client()
    print("Wayture Queue 管理工具")
    print(f"队列: {QUEUE_NAME}\n")

    commands = {
        "1": ("查看队列消息", cmd_list),
        "2": ("删除指定消息", cmd_delete),
        "3": ("手动添加任务", cmd_add),
        "4": ("清空队列", cmd_clear),
        "5": ("队列状态", cmd_stats),
        "q": ("退出", None),
    }

    while True:
        print("\n--- 操作菜单 ---")
        for k, (desc, _) in commands.items():
            print(f"  {k}. {desc}")

        choice = input("\n选择操作: ").strip()
        if choice == "q":
            print("再见")
            break

        entry = commands.get(choice)
        if entry and entry[1]:
            try:
                entry[1](client)
            except Exception as e:
                print(f"❌ 错误: {e}")
        else:
            print("无效选择")


if __name__ == "__main__":
    main()
