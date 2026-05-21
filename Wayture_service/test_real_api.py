"""
Wayture Service 实际 API 测试脚本
需要先启动服务: py -m uvicorn main:app --reload
需要先启动 worker: py worker.py

运行方式: py test_real_api.py
"""

import httpx
import json
import os
import sys
import time

BASE_URL = "http://127.0.0.1:8002"


def separator(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def print_json(data):
    print(json.dumps(data, ensure_ascii=False, indent=2))


def verify_url(client: httpx.Client, url: str, label: str = ""):
    full = url if url.startswith("http") else f"{BASE_URL}{url}"
    resp = client.get(full, timeout=300)
    tag = f" ({label})" if label else ""
    if resp.status_code == 200:
        print(f"  ✅ GET {url}{tag} -> {resp.status_code}, {len(resp.content)} bytes")
    else:
        print(f"  ❌ GET {url}{tag} -> {resp.status_code}")


def poll_task(client: httpx.Client, username: str, task_id: str, timeout: int = 600) -> dict | None:
    """轮询任务状态直到完成或超时。"""
    url = f"{BASE_URL}/api/tasks/{username}/{task_id}"
    start = time.time()
    while time.time() - start < timeout:
        resp = client.get(url, timeout=30)
        if resp.status_code != 200:
            print(f"  ❌ 查询任务失败: {resp.status_code}")
            return None
        task = resp.json()
        status = task.get("status", "")
        print(f"  ⏳ 任务 {task_id}: {status}")
        if status == "completed":
            return task
        if status == "failed":
            print(f"  ❌ 任务失败: {task.get('result', {}).get('error', '')[:200]}")
            return task
        time.sleep(5)
    print(f"  ❌ 任务超时 ({timeout}s)")
    return None


# ── 0. 获取地图 meta ───────────────────────────────────────────

def test_get_map_meta(client: httpx.Client) -> list:
    separator("0. 获取地图 meta  GET /api/map-meta")
    resp = client.get(f"{BASE_URL}/api/map-meta", timeout=10)
    print(f"状态码: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        print_json(data)
        print(f"✅ 获取地图 meta 成功，共 {len(data)} 个景点")
        return data
    print(f"❌ 失败: {resp.text}")
    return []


# ── 0.5 本地静态资源 ───────────────────────────────────────────

def test_local_static(client: httpx.Client):
    separator("0.5. 本地静态资源  GET /static/map.jpg")
    verify_url(client, "/static/map.jpg", "local asset via proxy")


# ── 1. 规划路线 ────────────────────────────────────────────────

def test_plan_route(client: httpx.Client, attractions: list) -> dict | None:
    separator("1. 规划路线  POST /api/plan-route")
    payload = {"username": "demo_user", "path_info": attractions}
    print(f"请求: {json.dumps(payload, ensure_ascii=False)[:200]}...")
    resp = client.post(f"{BASE_URL}/api/plan-route", json=payload, timeout=300)
    print(f"状态码: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        print_json(data)
        print("✅ 规划路线成功")
        return data
    print(f"❌ 失败: {resp.text}")
    return None


# ── 2. 生成明信片（异步）────────────────────────────────────────

def test_generate_postcard(client: httpx.Client, attractions: list, route_data: dict | None):
    separator("2. 生成明信片  POST /api/generate-postcard (异步)")

    if route_data is None:
        route_plan = [
            {"order": i + 1, "attraction": attractions[i], "tips": f"建议{i+1}"}
            for i in range(len(attractions))
        ]
    else:
        route_plan = route_data["route"]

    payload = {
        "username": "demo_user",
        "route_plan": route_plan,
        "attractions": attractions,
        "addition_prompt": "请加入中国水墨画风格元素，整体色调偏青绿山水",
    }

    print(f"请求: {json.dumps(payload, ensure_ascii=False)[:200]}...")
    resp = client.post(f"{BASE_URL}/api/generate-postcard", json=payload, timeout=300)
    print(f"状态码: {resp.status_code}")

    if resp.status_code == 200:
        data = resp.json()
        print_json(data)
        task_id = data.get("image_task_id", "")
        print(f"✅ 明信片文案已生成，图片任务: {task_id}")

        if task_id:
            print("等待图片生成...")
            task = poll_task(client, "demo_user", task_id)
            if task and task.get("status") == "completed":
                image_url = task.get("result", {}).get("image_url", "")
                if image_url:
                    verify_url(client, image_url, "postcard image from blob")
                print("✅ 明信片图片生成完成")
    else:
        print(f"❌ 失败: {resp.text}")


# ── 3. 上传图片 ────────────────────────────────────────────────

def test_upload_image(client: httpx.Client):
    separator("3. 上传图片  POST /api/upload-image")

    test_img_path = "test_upload.jpg"
    if not os.path.exists(test_img_path):
        print("下载测试图片...")
        img_resp = client.get(
            "https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?auto=format&fit=crop&w=400&q=60",
            timeout=30,
        )
        if img_resp.status_code == 200:
            with open(test_img_path, "wb") as f:
                f.write(img_resp.content)
            print(f"已保存测试图片: {test_img_path}")
        else:
            print("无法下载测试图片，使用占位图")
            import struct, zlib

            def make_png(w=2, h=2):
                raw = b""
                for _ in range(h):
                    raw += b"\x00" + b"\xff\x00\x00" * w

                def chunk(t, d):
                    c = t + d
                    return struct.pack(">I", len(d)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)

                return (
                    b"\x89PNG\r\n\x1a\n"
                    + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
                    + chunk(b"IDAT", zlib.compress(raw))
                    + chunk(b"IEND", b"")
                )

            with open(test_img_path, "wb") as f:
                f.write(make_png())

    with open(test_img_path, "rb") as f:
        resp = client.post(
            f"{BASE_URL}/api/upload-image",
            data={"username": "demo_user"},
            files={"file": ("test_photo.jpg", f, "image/jpeg")},
            timeout=300,
        )

    print(f"状态码: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        print_json(data)
        photo_url = data.get("url", "")
        if photo_url:
            verify_url(client, photo_url, "uploaded photo from blob")
        print("✅ 上传图片成功")
    else:
        print(f"❌ 失败: {resp.text}")


# ── 4. 获取图片列表 ────────────────────────────────────────────

def test_get_images(client: httpx.Client) -> list:
    separator("4. 获取图片  GET /api/images/demo_user")
    resp = client.get(f"{BASE_URL}/api/images/demo_user", timeout=10)
    print(f"状态码: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        print_json(data)
        print(f"✅ 获取图片成功，共 {len(data)} 张")
        return data
    print(f"❌ 失败: {resp.text}")
    return []


# ── 5. 生成图册（异步）─────────────────────────────────────────

def test_generate_gallery(client: httpx.Client, photos: list):
    separator("5. 生成图册  POST /api/generate-gallery (异步)")

    if not photos:
        print("⚠️  没有已上传的照片，跳过图册生成测试")
        return

    indices = [p["index"] for p in photos]
    payload = {"username": "demo_user", "selected_indices": indices}

    print(f"请求: {json.dumps(payload, ensure_ascii=False)}")
    resp = client.post(f"{BASE_URL}/api/generate-gallery", json=payload, timeout=300)
    print(f"状态码: {resp.status_code}")

    if resp.status_code == 200:
        data = resp.json()
        print_json(data)
        task_id = data.get("task_id", "")
        print(f"✅ 图册任务已提交: {task_id}")

        if task_id:
            print("等待图册生成...")
            task = poll_task(client, "demo_user", task_id)
            if task and task.get("status") == "completed":
                memory = task.get("result", {}).get("memory", {})
                print(f"回忆 ID: {memory.get('id')}")
                print(f"回忆标题: {memory.get('title')}")
                for img in memory.get("images", []):
                    verify_url(client, img.get("generated_url", ""), "gallery image from blob")
                print("✅ 图册生成完成")
    else:
        print(f"❌ 失败: {resp.text}")


# ── 6. 获取所有回忆 ────────────────────────────────────────────

def test_get_memories(client: httpx.Client):
    separator("6. 获取所有回忆  GET /api/memories/demo_user")
    resp = client.get(f"{BASE_URL}/api/memories/demo_user", timeout=10)
    print(f"状态码: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        print_json(data)
        print(f"✅ 获取回忆成功，共 {len(data)} 条回忆")
        for m in data:
            print(f"  - [{m['id']}] {m['title']}  ({m['generated_image_count']} 张图片, {m['created_at']})")
    else:
        print(f"❌ 失败: {resp.text}")


# ── 7. 获取所有任务 ────────────────────────────────────────────

def test_get_tasks(client: httpx.Client):
    separator("7. 获取所有任务  GET /api/tasks/demo_user")
    resp = client.get(f"{BASE_URL}/api/tasks/demo_user", timeout=10)
    print(f"状态码: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        print_json(data)
        print(f"✅ 获取任务成功，共 {len(data)} 个任务")
        for t in data:
            print(f"  - [{t['task_id']}] {t['task_type']}  状态={t['status']}")
    else:
        print(f"❌ 失败: {resp.text}")


# ── 主流程 ─────────────────────────────────────────────────────

def main():
    print("Wayture Service 实际 API 测试")
    print(f"目标地址: {BASE_URL}")

    with httpx.Client() as client:
        try:
            client.get(f"{BASE_URL}/docs", timeout=5)
        except httpx.ConnectError:
            print(f"\n❌ 无法连接 {BASE_URL}")
            print("请先启动服务: py -m uvicorn main:app --reload")
            sys.exit(1)

        print("✅ 服务已连接\n")

        # 0. 获取地图 meta
        attractions = test_get_map_meta(client)
        input("按回车继续...")

        # 0.5 本地静态资源
        test_local_static(client)
        input("按回车继续...")

        # 1. 规划路线
        route_data = test_plan_route(client, attractions)
        input("按回车继续...")

        # 2. 生成明信片（异步）
        test_generate_postcard(client, attractions, route_data)
        input("按回车继续...")

        # 3. 上传图片
        test_upload_image(client)
        input("按回车继续...")

        # 4. 获取图片列表
        photos = test_get_images(client)
        input("按回车继续...")

        # 5. 生成图册（异步）
        test_generate_gallery(client, photos)
        input("按回车继续...")

        # 6. 获取所有回忆
        test_get_memories(client)
        input("按回车继续...")

        # 7. 获取所有任务
        test_get_tasks(client)

        separator("全部测试完成")


if __name__ == "__main__":
    main()
