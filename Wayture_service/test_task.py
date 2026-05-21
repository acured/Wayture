"""
测试任务提交 + 轮询状态

运行前确保:
  1. API 已启动:   py -m uvicorn main:app --reload --port 8002
  2. Worker 已启动: py worker.py

运行: py test_task.py
"""
import httpx
import json
import time
import sys

BASE_URL = "http://127.0.0.1:8002"


def print_json(data):
    print(json.dumps(data, ensure_ascii=False, indent=2))


def poll_task(client: httpx.Client, username: str, task_id: str, timeout: int = 600):
    url = f"{BASE_URL}/api/tasks/{username}/{task_id}"
    start = time.time()
    while time.time() - start < timeout:
        resp = client.get(url, timeout=30)
        if resp.status_code != 200:
            print(f"  ❌ 查询任务失败: {resp.status_code} {resp.text}")
            return None
        task = resp.json()
        status = task.get("status", "")
        elapsed = int(time.time() - start)
        print(f"  [{elapsed:>3d}s] 任务 {task_id}: {status}")
        if status == "completed":
            print("\n✅ 任务完成，结果:")
            print_json(task.get("result"))
            return task
        if status == "failed":
            print(f"\n❌ 任务失败:")
            print_json(task.get("result"))
            return task
        time.sleep(5)
    print(f"\n❌ 超时 ({timeout}s)")
    return None


def test_postcard_task(client: httpx.Client):
    print("=" * 50)
    print("  测试: 提交明信片任务 + 轮询状态")
    print("=" * 50)

    # 1. 获取景点
    print("\n[1] 获取景点列表...")
    resp = client.get(f"{BASE_URL}/api/map-meta", timeout=10)
    if resp.status_code != 200:
        print(f"❌ 获取景点失败: {resp.status_code}")
        return
    attractions = resp.json()
    print(f"  共 {len(attractions)} 个景点")

    # 2. 提交明信片任务
    print("\n[2] 提交明信片生成...")
    payload = {
        "username": "demo_user",
        "route_plan": [
            {"order": i + 1, "attraction": a, "tips": f"建议游玩"}
            for i, a in enumerate(attractions[:3])
        ],
        "attractions": attractions,
        "addition_prompt": "中国水墨画风格",
    }
    resp = client.post(f"{BASE_URL}/api/generate-postcard", json=payload, timeout=300)
    print(f"  状态码: {resp.status_code}")
    if resp.status_code != 200:
        print(f"  ❌ 提交失败: {resp.text}")
        return

    data = resp.json()
    task_id = data.get("image_task_id", "")
    print(f"  文案标题: {data.get('title', '')}")
    print(f"  图片任务ID: {task_id}")

    if not task_id:
        print("  ⚠️ 没有返回 task_id，可能文案生成就失败了")
        return

    # 3. 轮询任务状态
    print(f"\n[3] 轮询任务状态 (task_id={task_id})...")
    poll_task(client, "demo_user", task_id)

    # 4. 查看所有任务
    print(f"\n[4] 查看所有任务...")
    resp = client.get(f"{BASE_URL}/api/tasks/demo_user", timeout=10)
    if resp.status_code == 200:
        tasks = resp.json()
        for t in tasks:
            print(f"  [{t['task_id']}] {t['task_type']}  status={t['status']}  created={t['created_at']}")


def main():
    print(f"目标: {BASE_URL}\n")
    with httpx.Client() as client:
        try:
            client.get(f"{BASE_URL}/docs", timeout=5)
        except httpx.ConnectError:
            print(f"❌ 无法连接 {BASE_URL}，请先启动服务")
            sys.exit(1)
        print("✅ 服务已连接\n")
        test_postcard_task(client)


if __name__ == "__main__":
    main()
