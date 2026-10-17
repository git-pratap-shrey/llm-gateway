#!/usr/bin/env python3
"""tests/multimodal/test_image_python.py

End-to-end multimodal test using httpx.

Flow
----
1. Download a random sample image from Picsum Photos.
2. Base64-encode it and set it as the environment variable BASE64_IMAGE
   (so you can inspect or reuse it after the run).
3. POST an OpenAI-compatible multimodal request to the gateway's
   /v1/chat/completions endpoint.
4. Pretty-print the JSON response.

Usage
-----
    python tests/multimodal/test_image_python.py [gateway_url] [model]

Defaults
--------
    gateway_url : http://localhost:8000
    model       : ollama_cloud/gemma4:cloud
"""

from __future__ import annotations

import base64
import json
import os
import random
import sys

try:
    import httpx
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "httpx", "-q"])
    import httpx


# ── Configuration ──────────────────────────────────────────────────────────────
GATEWAY = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
MODEL   = sys.argv[2] if len(sys.argv) > 2 else "ollama_cloud/gemma4:cloud"
ENDPOINT = f"{GATEWAY}/v1/chat/completions"

PROMPT = "Extract all text from this page. Return markdown text."


def download_image(seed: int | None = None) -> bytes:
    """Download a small sample image from Picsum Photos."""
    seed = seed or random.randint(1, 10_000)
    url = f"https://picsum.photos/seed/{seed}/400/300"
    print(f"→ Downloading image (seed={seed}) from {url} …")
    with httpx.Client(follow_redirects=True, timeout=30) as client:
        resp = client.get(url)
        resp.raise_for_status()
    print(f"  {len(resp.content):,} bytes, content-type={resp.headers.get('content-type', '?')}")
    return resp.content


def encode_image(image_bytes: bytes, mime: str = "image/jpeg") -> str:
    """Return a data-URI string for the image."""
    b64 = base64.b64encode(image_bytes).decode("ascii")
    os.environ["BASE64_IMAGE"] = b64          # export for shell inspection
    print(f"→ BASE64_IMAGE set ({len(b64):,} chars)")
    return f"data:{mime};base64,{b64}"


def send_multimodal_request(data_uri: str) -> dict:
    """POST the multimodal request and return the parsed JSON response."""
    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": PROMPT},
                    {"type": "image_url", "image_url": {"url": data_uri}},
                ],
            }
        ],
        "temperature": 0,
    }

    print(f"\n→ Sending multimodal request to {ENDPOINT} (model: {MODEL}) …\n")
    with httpx.Client(timeout=120) as client:
        resp = client.post(
            ENDPOINT,
            json=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer ollama",
            },
        )

    print(f"  HTTP {resp.status_code}")
    return resp.json()


def main() -> None:
    image_bytes = download_image()
    data_uri    = encode_image(image_bytes)
    response    = send_multimodal_request(data_uri)

    print("\n── Response ─────────────────────────────────────────────────────────────")
    print(json.dumps(response, indent=2, ensure_ascii=False))

    # Surface the model's reply at the top level for readability.
    try:
        content = response["choices"][0]["message"]["content"]
        print("\n── Model output ─────────────────────────────────────────────────────────")
        print(content)
    except (KeyError, IndexError, TypeError):
        pass


if __name__ == "__main__":
    main()
