from __future__ import annotations

import sys
from pathlib import Path
from urllib.request import Request, urlopen

URL = "https://huggingface.co/bartowski/Qwen2.5-Coder-1.5B-Instruct-GGUF/resolve/main/Qwen2.5-Coder-1.5B-Instruct-Q4_K_M.gguf"
ROOT = Path(__file__).resolve().parent
TARGET = ROOT / "AI-Runtimes" / "models" / "Qwen2.5-Coder-1.5B-Instruct-Q4_K_M.gguf"

if TARGET.is_file() and TARGET.stat().st_size > 100 * 1024 * 1024:
    print(f"Model zaten mevcut: {TARGET}")
    raise SystemExit(0)

TARGET.parent.mkdir(parents=True, exist_ok=True)
temporary = TARGET.with_suffix(TARGET.suffix + ".part")
request = Request(URL, headers={"User-Agent": "LocalQwenAgent/1.0"})
with urlopen(request, timeout=60) as response, temporary.open("wb") as output:
    total = int(response.headers.get("Content-Length", "0"))
    downloaded = 0
    while True:
        chunk = response.read(1024 * 1024)
        if not chunk:
            break
        output.write(chunk)
        downloaded += len(chunk)
        if total:
            print(f"{downloaded / total:.1%}", end="\r", flush=True)
temporary.replace(TARGET)
print(f"Model indirildi: {TARGET}")
