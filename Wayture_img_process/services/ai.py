from __future__ import annotations

import base64


def generate_image(client, deployment, prompt, *, size="1536x1024", input_images=None, n=1):
    from io import BytesIO
    from PIL import Image

    MAX_REF_SIZE = 1024

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

        resp = client.images.edit(
            model=deployment,
            image=image_files if len(image_files) > 1 else image_files[0],
            prompt=prompt,
            n=n,
            size=size,
        )
    else:
        resp = client.images.generate(
            model=deployment, prompt=prompt, size=size, n=n,
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
