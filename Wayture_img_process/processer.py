"""
Wayture Debug Processor — 通过 task_id 执行单个任务，结果保存到本地。
不读取 queue，不上传结果，纯本地 debug 用。

用法: python processer.py <username> <task_id>
结果保存到: ./debug_output/<task_id>/
"""
from __future__ import annotations

import asyncio
import base64
import json
import sys
import time
import traceback
from datetime import datetime
from io import BytesIO
from pathlib import Path

# ── 常量 ──────────────────────────────────────────────────────

STORAGE_ACCOUNT = "wayturestorage"
OPENAI_MI_CLIENT_ID = "dc1352c5-927a-4fa1-93c4-eecb03417716"
OPENAI_ENDPOINT = "https://aoai-svc-0.openai.azure.com/"
OPENAI_API_VERSION = "2025-04-01-preview"
OPENAI_DEPLOYMENT = "gpt-image-2-01"

STATIC_DIR = Path(__file__).resolve().parent / "static"
OUTPUT_DIR = Path(__file__).resolve().parent / "debug_output"

MAX_REF_SIZE = 1024


# ── log ───────────────────────────────────────────────────────

def log(stage: str, msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] [{stage}] {msg}")


# ── Blob 读取（只读，async）────────────────────────────────────

_blob_client = None
_blob_credential = None

def _get_blob_client():
    global _blob_client, _blob_credential
    if _blob_client is None:
        from azure.identity.aio import DefaultAzureCredential
        from azure.storage.blob.aio import BlobServiceClient
        _blob_credential = DefaultAzureCredential()
        _blob_client = BlobServiceClient(
            account_url=f"https://{STORAGE_ACCOUNT}.blob.core.windows.net",
            credential=_blob_credential,
        )
    return _blob_client


async def close_blob_client():
    global _blob_client, _blob_credential
    if _blob_client is not None:
        await _blob_client.close()
        _blob_client = None
    if _blob_credential is not None:
        await _blob_credential.close()
        _blob_credential = None


async def download_blob(container: str, blob_path: str) -> bytes:
    blob = _get_blob_client().get_blob_client(container, blob_path)
    stream = await blob.download_blob()
    return await stream.readall()


async def read_json_blob(container: str, blob_path: str):
    raw = await download_blob(container, blob_path)
    return json.loads(raw)


# ── OpenAI Image 客户端 ───────────────────────────────────────

_openai_client = None

def _get_openai_client():
    global _openai_client
    if _openai_client is None:
        from azure.identity import ManagedIdentityCredential, get_bearer_token_provider
        from openai import AzureOpenAI
        credential = ManagedIdentityCredential(client_id=OPENAI_MI_CLIENT_ID)
        token_provider = get_bearer_token_provider(
            credential, "https://cognitiveservices.azure.com/.default"
        )
        _openai_client = AzureOpenAI(
            azure_endpoint=OPENAI_ENDPOINT,
            azure_ad_token_provider=token_provider,
            api_version=OPENAI_API_VERSION,
        )
    return _openai_client


def generate_image(prompt: str, *, size: str = "1536x1024", input_images: list[bytes] | None = None):
    from PIL import Image

    client = _get_openai_client()

    if input_images:
        image_files = []
        for i, img in enumerate(input_images):
            pic = Image.open(BytesIO(img))
            if pic.mode not in ("RGB", "RGBA"):
                pic = pic.convert("RGBA")
            if max(pic.size) > MAX_REF_SIZE:
                pic.thumbnail((MAX_REF_SIZE, MAX_REF_SIZE), Image.LANCZOS)
            buf = BytesIO()
            buf.name = f"input_{i}.png"
            pic.save(buf, format="PNG")
            buf.seek(0)
            image_files.append(buf)

        log("OPENAI", f"images.edit: {len(image_files)} 张参考图, size={size}")
        resp = client.images.edit(
            model=OPENAI_DEPLOYMENT,
            image=image_files if len(image_files) > 1 else image_files[0],
            prompt=prompt,
            n=1,
            size=size,
        )
    else:
        log("OPENAI", f"images.generate: size={size}")
        resp = client.images.generate(
            model=OPENAI_DEPLOYMENT, prompt=prompt, size=size, n=1,
        )

    results: list[bytes] = []
    for item in resp.data:
        if hasattr(item, "b64_json") and item.b64_json:
            results.append(base64.b64decode(item.b64_json))
        elif hasattr(item, "url") and item.url:
            import httpx
            with httpx.Client() as http:
                dl = http.get(item.url)
                results.append(dl.content)
    return results


# ── 任务执行 ──────────────────────────────────────────────────

async def execute_task(username: str, task_id: str, out_dir: Path):
    log("LOAD", f"读取任务: data/{username}/tasks/{task_id}/task.json")
    task_data = await read_json_blob("data", f"{username}/tasks/{task_id}/task.json")

    task_type = task_data.get("task_type", "unknown")
    log("INFO", f"task_type={task_type}  username={username}")

    prompt = task_data.get("prompt", "")
    size = task_data.get("size", "1024x1024")

    # 保存 prompt 到本地
    if prompt:
        (out_dir / "prompt.txt").write_text(prompt, encoding="utf-8")
        log("SAVE", "prompt.txt")

    # 保存完整 task_data
    (out_dir / "task_data.json").write_text(
        json.dumps(task_data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    log("SAVE", "task_data.json")

    # ── 收集参考图片 ──
    input_images: list[bytes] = []

    # postcard/postcard_banner: 从本地 static 读取
    for local_path in task_data.get("local_ref_images", []):
        full_path = STATIC_DIR / local_path
        if full_path.exists():
            input_images.append(full_path.read_bytes())
            log("REF", f"本地: {local_path} ({len(input_images[-1]) // 1024}KB)")
        else:
            log("WARN", f"本地文件不存在: {full_path}")

    # journal: 从 blob 读取
    for blob_path in task_data.get("ref_images", []):
        try:
            img_bytes = await download_blob("data", blob_path)
            input_images.append(img_bytes)
            log("REF", f"Blob: {blob_path} ({len(img_bytes) // 1024}KB)")
        except Exception as e:
            log("WARN", f"Blob 下载失败: {blob_path} — {e}")

    # gallery/album: 子任务
    sub_tasks = task_data.get("sub_tasks", [])
    if sub_tasks:
        log("INFO", f"共 {len(sub_tasks)} 个子任务")
        for idx, sub in enumerate(sub_tasks, 1):
            sub_prompt = sub.get("prompt", "")
            sub_size = sub.get("size", "1024x1024")
            log("SUB", f"[{idx}/{len(sub_tasks)}] 开始生成...")

            start = time.time()
            try:
                result = generate_image(sub_prompt, size=sub_size)
                elapsed = time.time() - start
                filename = f"{task_id}_sub{idx}.png"
                (out_dir / filename).write_bytes(result[0])
                log("DONE", f"[{idx}] {filename} ({elapsed:.1f}s, {len(result[0]) // 1024}KB)")
            except Exception:
                log("ERROR", f"[{idx}] 生成失败")
                traceback.print_exc()
        return

    # ── 单任务生成 ──
    log("GEN", f"开始生成图片... ({len(input_images)} 张参考图)")
    start = time.time()
    result = generate_image(prompt, size=size, input_images=input_images or None)
    elapsed = time.time() - start

    filename = f"{task_id}.png"
    (out_dir / filename).write_bytes(result[0])
    log("DONE", f"{filename} ({elapsed:.1f}s, {len(result[0]) // 1024}KB)")


# ── 入口 ──────────────────────────────────────────────────────

async def main():
    if len(sys.argv) < 3:
        print("用法: python processer.py <username> <task_id>")
        print("示例: python processer.py 'John Doe' abc123def456")
        sys.exit(1)

    username = sys.argv[1]
    task_id = sys.argv[2]

    out_dir = OUTPUT_DIR / task_id
    out_dir.mkdir(parents=True, exist_ok=True)

    log("START", f"task_id={task_id}  output={out_dir}")

    try:
        await execute_task(username, task_id, out_dir)
    except Exception:
        log("CRASH", "执行失败")
        traceback.print_exc()
        sys.exit(1)
    finally:
        await close_blob_client()

    log("END", "完成")


if __name__ == "__main__":
    asyncio.run(main())
