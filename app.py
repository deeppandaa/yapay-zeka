from __future__ import annotations

import io
import base64
import ctypes
import importlib.util
import math
import ipaddress
import json
import os
import re
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import uuid
import shutil
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from docx import Document
from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from openpyxl import load_workbook
from pptx import Presentation
from pydantic import BaseModel
from pypdf import PdfReader, PdfWriter
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from PIL import Image

from agent_orchestrator import decide, plan_for, system_prompt
from agent_tools import AgentTools

load_dotenv()

ROOT = Path(__file__).resolve().parent
WORKSPACE_ROOT = Path(os.getenv("WORKSPACE_ROOT", str(ROOT))).resolve()
MEMORY_DB = ROOT / os.getenv("MEMORY_DB", "memory.db")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3.6:latest")
OLLAMA_CODE_MODEL = os.getenv("OLLAMA_CODE_MODEL", "codellama:7b")
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
CONTINUE_MODEL = os.getenv("CONTINUE_MODEL", OLLAMA_CODE_MODEL)
OLLAMA_TIMEOUT_SECONDS = int(os.getenv("OLLAMA_TIMEOUT_SECONDS", "600"))
MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_MB", "50")) * 1024 * 1024
AGENT_DEV_MODE = os.getenv("AGENT_DEV_MODE", "off").strip().lower()
REQUIRE_MEMORY_APPROVAL = os.getenv("REQUIRE_MEMORY_APPROVAL", "off").strip().lower() in {"1", "true", "yes", "on"}

app = FastAPI(title="LocalQwenAgent")
app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
AGENT_TOOLS = AgentTools(WORKSPACE_ROOT)
RESEARCH_JOBS: dict[str, dict[str, Any]] = {}
RESEARCH_LOCK = threading.Lock()


class ChatRequest(BaseModel):
    message: str
    memory: bool = True
    approve_memory: bool = False


class MemoryRequest(BaseModel):
    note: str
    category: str = "general"
    project: str = ""
    source: str = "user"


class ResearchRequest(BaseModel):
    question: str
    urls: list[str]


class GitHubResearchRequest(BaseModel):
    question: str
    repositories: list[str]


class BrowserRequest(BaseModel):
    url: str


class ToolRequest(BaseModel):
    command: list[str]
    approved: bool = False


class FileWriteRequest(BaseModel):
    path: str
    content: str


class AgentPlanRequest(BaseModel):
    message: str
    approved: bool = False


class AgentExecuteRequest(BaseModel):
    command: list[str]
    approved: bool = False
    task_id: str | None = None


class AgentGenerateRequest(BaseModel):
    request: str
    project_path: str = ""


class AgentApplyRequest(BaseModel):
    files: list[dict[str, str]]
    approved: bool = False
    task_id: str | None = None


class AgentRollbackRequest(BaseModel):
    task_id: str


class FileWorkflowRequest(BaseModel):
    path: str
    action: str = "read"
    content: str = ""
    approved: bool = False


class AgentProfileExecuteRequest(BaseModel):
    profile: str
    action: str = "test"
    approved: bool = False


class SelfAuditRequest(BaseModel):
    run_tests: bool = True


class MediaRequest(BaseModel):
    filename: str
    transcribe: bool = True


class OpenAIChatRequest(BaseModel):
    model: str = "local-qwen"
    messages: list[dict[str, Any]]
    temperature: float | None = None
    max_tokens: int | None = None
    stream: bool = False


class ModelProfileRequest(BaseModel):
    profile: str


class EmbeddingInstallRequest(BaseModel):
    approved: bool = False


class SetupRequest(BaseModel):
    approved: bool = False


class ReportExportRequest(BaseModel):
    title: str = "LocalQwenAgent Raporu"
    sources: list[str] = []
    report: dict[str, Any]
    format: str = "md"


def db() -> sqlite3.Connection:
    connection = sqlite3.connect(MEMORY_DB)
    connection.execute(
        "CREATE TABLE IF NOT EXISTS memories (id INTEGER PRIMARY KEY, note TEXT NOT NULL, category TEXT NOT NULL DEFAULT 'general', project TEXT NOT NULL DEFAULT '', source TEXT NOT NULL DEFAULT 'user', created_at TEXT DEFAULT CURRENT_TIMESTAMP)"
    )
    columns = {row[1] for row in connection.execute("PRAGMA table_info(memories)").fetchall()}
    for name, definition in (("category", "TEXT NOT NULL DEFAULT 'general'"), ("project", "TEXT NOT NULL DEFAULT ''"), ("source", "TEXT NOT NULL DEFAULT 'user'")):
        if name not in columns:
            connection.execute(f"ALTER TABLE memories ADD COLUMN {name} {definition}")
    rows = connection.execute("SELECT id, note, category, project, source FROM memories ORDER BY id").fetchall()
    seen: set[tuple[str, str, str, str]] = set()
    duplicate_ids: list[int] = []
    for row_id, note, category, project, source in rows:
        key = (
            re.sub(r"\s+", " ", note or "").strip(),
            "general" if category in (None, "", "None") else str(category),
            "" if project in (None, "", "None") else str(project),
            "user" if source in (None, "", "None") else str(source),
        )
        if key in seen:
            duplicate_ids.append(row_id)
        else:
            seen.add(key)
    if duplicate_ids:
        connection.executemany("DELETE FROM memories WHERE id = ?", [(row_id,) for row_id in duplicate_ids])
    connection.execute(
        "CREATE TABLE IF NOT EXISTS operation_journal (id INTEGER PRIMARY KEY, operation TEXT NOT NULL, reasoning TEXT NOT NULL, result TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP)"
    )
    connection.execute(
        "CREATE TABLE IF NOT EXISTS task_records (task_id TEXT PRIMARY KEY, request TEXT NOT NULL, intent TEXT NOT NULL, plan TEXT NOT NULL, approved INTEGER NOT NULL DEFAULT 0, status TEXT NOT NULL, commands TEXT NOT NULL DEFAULT '[]', changed_files TEXT NOT NULL DEFAULT '[]', tests TEXT NOT NULL DEFAULT '[]', result TEXT NOT NULL DEFAULT '', created_at TEXT DEFAULT CURRENT_TIMESTAMP, updated_at TEXT DEFAULT CURRENT_TIMESTAMP)"
    )
    connection.execute(
        "CREATE TABLE IF NOT EXISTS job_records (job_id TEXT PRIMARY KEY, kind TEXT NOT NULL, question TEXT NOT NULL, urls TEXT NOT NULL DEFAULT '[]', status TEXT NOT NULL, artifact_dir TEXT NOT NULL, error TEXT NOT NULL DEFAULT '', created_at TEXT DEFAULT CURRENT_TIMESTAMP, updated_at TEXT DEFAULT CURRENT_TIMESTAMP)"
    )
    return connection


def memory_context() -> str:
    with db() as connection:
        rows = connection.execute(
            "SELECT note FROM memories ORDER BY id DESC LIMIT 20"
        ).fetchall()
    return "\n".join(f"- {row[0]}" for row in rows)


def retrieved_memory_context(query: str, limit: int = 8) -> str:
    terms = [term.lower() for term in re.findall(r"[\w-]{3,}", query) if term.lower() not in {"bir", "icin", "ile", "the", "and"}]
    if not terms:
        return memory_context()
    clauses = " OR ".join("note LIKE ?" for _ in terms)
    with db() as connection:
        rows = connection.execute(
            f"SELECT note, category, project, source FROM memories WHERE {clauses} ORDER BY id DESC LIMIT ?",
            [*(f"%{term}%" for term in terms), limit],
        ).fetchall()
    return "\n".join(
        f"- [{category}/{project or 'genel'}/{source}] {note}"
        for note, category, project, source in rows
    ) or memory_context()


def ollama_embed(inputs: list[str]) -> list[list[float]]:
    request = Request(
        f"{OLLAMA_BASE_URL}/api/embed",
        data=json.dumps({"model": OLLAMA_EMBED_MODEL, "input": inputs}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=30) as response:
        result = json.loads(response.read().decode("utf-8"))
    embeddings = result.get("embeddings")
    if not isinstance(embeddings, list) or len(embeddings) != len(inputs):
        raise ValueError("Embedding modeli gecersiz yanit verdi.")
    return embeddings


def cosine_similarity(left: list[float], right: list[float]) -> float:
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    return dot / (left_norm * right_norm) if left_norm and right_norm else 0.0


def journal_operation(operation: str, reasoning: str, result: str) -> None:
    with db() as connection:
        connection.execute(
            "INSERT INTO operation_journal(operation, reasoning, result) VALUES (?, ?, ?)",
            (operation[:500], reasoning[:4000], result[:12000]),
        )


def update_task(task_id: str | None, **fields: Any) -> None:
    if not task_id or not fields:
        return
    allowed = {"approved", "status", "commands", "changed_files", "tests", "result"}
    updates = {key: value for key, value in fields.items() if key in allowed}
    if not updates:
        return
    assignments = ", ".join(f"{key} = ?" for key in updates) + ", updated_at = CURRENT_TIMESTAMP"
    with db() as connection:
        connection.execute(
            f"UPDATE task_records SET {assignments} WHERE task_id = ?",
            [*updates.values(), task_id],
        )


def operation_context() -> str:
    with db() as connection:
        rows = connection.execute(
            "SELECT operation, reasoning, result FROM operation_journal ORDER BY id DESC LIMIT 10"
        ).fetchall()
    return "\n".join(
        f"- {operation}: neden={reasoning}; sonuc={result}"
        for operation, reasoning, result in rows
    )


def workspace_context(query: str) -> str:
    terms = {word.lower() for word in query.split() if len(word) >= 3}
    if not terms or not WORKSPACE_ROOT.is_dir():
        return ""
    snippets: list[str] = []
    allowed = {".py", ".md", ".txt", ".json", ".ts", ".tsx", ".ps1"}
    for path in WORKSPACE_ROOT.rglob("*"):
        if len(snippets) >= 8 or not path.is_file() or path.suffix.lower() not in allowed:
            continue
        try:
            if path.stat().st_size > 300_000:
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        lower = text.lower()
        if any(term in lower for term in terms):
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            matches = [line for line in lines if any(term in line.lower() for term in terms)]
            if matches:
                snippets.append(f"[{path.relative_to(WORKSPACE_ROOT)}] " + " ".join(matches[:3]))
    return "\n".join(snippets)


def call_ollama(
    messages: list[dict[str, Any]],
    json_format: bool = False,
    model: str | None = None,
    num_ctx: int | None = None,
    num_predict: int | None = None,
    timeout: int | None = None,
) -> str:
    payload = {
        "model": model or OLLAMA_MODEL,
        "messages": messages,
        "stream": False,
        "think": False,
    }
    options: dict[str, int] = {}
    if num_ctx is not None:
        options["num_ctx"] = num_ctx
    if num_predict is not None:
        options["num_predict"] = num_predict
    if options:
        payload["options"] = options
    if json_format:
        payload["format"] = "json"
    request = Request(
        f"{OLLAMA_BASE_URL}/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout or OLLAMA_TIMEOUT_SECONDS) as response:
            result = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        raise HTTPException(503, f"Ollama baglantisi kurulamadi: {exc}") from exc
    try:
        message = result["message"]
        content = str(message.get("content", "") or "").strip()
        if content:
            return content
        thinking = str(message.get("thinking", "") or "").strip()
        if thinking:
            return thinking
        return "Model bos yanit dondurdu."
    except (KeyError, TypeError) as exc:
        raise HTTPException(502, "Ollama gecersiz yanit dondurdu.") from exc


def extract_json_object(text: str) -> dict[str, Any]:
    value = text.strip()
    if value.startswith("```"):
        value = re.sub(r"^```(?:json)?\s*|\s*```$", "", value, flags=re.IGNORECASE | re.DOTALL).strip()
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        try:
            from json_repair import repair_json
            parsed = json.loads(repair_json(value))
        except Exception:
            parsed = None
        if isinstance(parsed, dict):
            return parsed
        start, end = value.find("{"), value.rfind("}")
        if start < 0 or end <= start:
            code_blocks = re.findall(r"```(?:python|py)?\s*(.*?)```", value, flags=re.IGNORECASE | re.DOTALL)
            if code_blocks:
                return {"summary": "Model kod blogu uretti.", "files": [{"path": "main.py", "content": code_blocks[0].strip()}], "tests": []}
            raise HTTPException(502, "Model gecerli JSON dosya plani dondurmedi.")
        parsed = json.loads(value[start:end + 1])
    if not isinstance(parsed, dict):
        raise HTTPException(502, "Model dosya plani nesne olmali.")
    return parsed


class _PageTextParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts: list[str] = []
        self.skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag.lower() in {"script", "style", "noscript", "svg"}:
            self.skip_depth += 1

    def handle_endtag(self, tag):
        if tag.lower() in {"script", "style", "noscript", "svg"} and self.skip_depth:
            self.skip_depth -= 1

    def handle_data(self, data):
        if not self.skip_depth:
            clean = re.sub(r"\s+", " ", data).strip()
            if clean:
                self.parts.append(clean)


def fetch_web_page(url: str) -> str:
    parsed = urlparse(url.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("Yalnizca http/https URL kullanilabilir.")
    host = parsed.hostname.lower()
    if host in {"localhost", "127.0.0.1", "::1"}:
        raise ValueError("Yerel adresler web arastirmasinda engellendi.")
    try:
        address = ipaddress.ip_address(host)
        if address.is_private or address.is_loopback or address.is_link_local:
            raise ValueError("Ozel ag adresleri engellendi.")
    except ValueError as exc:
        if "engellendi" in str(exc):
            raise
    request = Request(url, headers={"User-Agent": "LocalQwenAgent/0.1"})
    with urlopen(request, timeout=15) as response:
        raw = response.read(250_000)
    html = raw.decode("utf-8", errors="replace")
    try:
        import trafilatura
        extracted = trafilatura.extract(html, include_comments=False, include_tables=True)
        if extracted:
            return extracted[:40_000]
    except ImportError:
        pass
    parser = _PageTextParser()
    parser.feed(html)
    return " ".join(parser.parts)[:40_000]


def extract_document_text(data: bytes, suffix: str) -> str:
    if suffix == ".pdf":
        reader = PdfReader(io.BytesIO(data))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    if suffix in {".docx"}:
        document = Document(io.BytesIO(data))
        return "\n".join(paragraph.text for paragraph in document.paragraphs)
    if suffix in {".pptx"}:
        presentation = Presentation(io.BytesIO(data))
        return "\n".join(
            shape.text for slide in presentation.slides for shape in slide.shapes if hasattr(shape, "text")
        )
    if suffix in {".xlsx", ".xlsm"}:
        workbook = load_workbook(io.BytesIO(data), read_only=True, data_only=True)
        rows = []
        for sheet in workbook.worksheets:
            rows.append(f"[{sheet.title}]")
            rows.extend(" | ".join(str(cell.value or "") for cell in row) for row in sheet.iter_rows())
        return "\n".join(rows)
    if suffix in {".txt", ".md", ".py", ".json", ".ts", ".tsx"}:
        return data.decode("utf-8", errors="replace")
    return ""


def document_structure(data: bytes, suffix: str) -> str:
    """Return a compact structural description alongside extracted text."""
    if suffix == ".pdf":
        reader = PdfReader(io.BytesIO(data))
        return f"PDF: sayfa_sayisi={len(reader.pages)}"
    if suffix == ".docx":
        document = Document(io.BytesIO(data))
        tables = sum(1 for _ in document.tables)
        return f"DOCX: paragraf_sayisi={len(document.paragraphs)}, tablo_sayisi={tables}"
    if suffix == ".pptx":
        presentation = Presentation(io.BytesIO(data))
        shapes = sum(len(slide.shapes) for slide in presentation.slides)
        return f"PPTX: slayt_sayisi={len(presentation.slides)}, nesne_sayisi={shapes}"
    if suffix in {".xlsx", ".xlsm"}:
        workbook = load_workbook(io.BytesIO(data), read_only=True, data_only=True)
        sheets = [f"{sheet.title}:{sheet.max_row}x{sheet.max_column}" for sheet in workbook.worksheets]
        return "XLSX: sayfalar=" + ", ".join(sheets)
    if suffix in {".png", ".jpg", ".jpeg", ".webp"}:
        image = Image.open(io.BytesIO(data))
        return f"Gorsel: format={image.format}, boyut={image.width}x{image.height}, mod={image.mode}"
    return f"Metin dosyasi: uzanti={suffix}, byte={len(data)}"


def optional_ocr(data: bytes, suffix: str) -> dict[str, Any]:
    if suffix not in {".png", ".jpg", ".jpeg", ".webp", ".pdf"}:
        return {"available": False, "text": "", "reason": "OCR bu dosya turu icin desteklenmiyor."}
    try:
        import pytesseract
        tesseract_path = find_tesseract()
        if tesseract_path:
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
        if suffix == ".pdf":
            return {"available": False, "text": "", "reason": "PDF OCR icin sayfa rasterlastirma gerekiyor."}
        image = Image.open(io.BytesIO(data))
        return {"available": True, "text": pytesseract.image_to_string(image, lang="eng")[:20_000], "reason": ""}
    except ImportError:
        return {"available": False, "text": "", "reason": "pytesseract veya Tesseract OCR kurulu degil."}
    except Exception as exc:
        return {"available": False, "text": "", "reason": f"OCR basarisiz: {exc}"}


def find_tesseract() -> str:
    candidates = [
        shutil.which("tesseract"),
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    ]
    return next((path for path in candidates if path and Path(path).is_file()), "")


def report_markdown(title: str, report: dict[str, Any], sources: list[str]) -> str:
    lines = [f"# {title}", "", "## Kaynaklar"]
    lines.extend(f"- {source}" for source in sources or ["Belirtilmedi"])
    lines.extend(["", "## Rapor", "", "```json", json.dumps(report, ensure_ascii=False, indent=2), "```", ""])
    return "\n".join(lines)


def call_ollama_vision(data: bytes, prompt: str, suffix: str) -> str:
    encoded = base64.b64encode(data).decode("ascii")
    payload = {
        "model": OLLAMA_MODEL,
        "messages": [{"role": "user", "content": prompt, "images": [encoded]}],
        "stream": False,
    }
    request = Request(
        f"{OLLAMA_BASE_URL}/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=180) as response:
            result = json.loads(response.read().decode("utf-8"))
        message = result.get("message", {})
        return str(message.get("content") or message.get("thinking") or "Gorsel yaniti bos.")
    except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        raise HTTPException(503, f"Vision modeli yaniti alinamadi: {exc}") from exc


def github_sources(repository: str) -> list[str]:
    """Map a public GitHub repository URL to readable public HTTP sources."""
    value = repository.strip().rstrip("/")
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or parsed.hostname != "github.com":
        raise ValueError("Public GitHub repo URL gerekli.")
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) < 2:
        raise ValueError("GitHub repo URL owner/repo icermeli.")
    owner, repo = parts[0], parts[1].removesuffix(".git")
    return [
        f"https://github.com/{owner}/{repo}",
        f"https://raw.githubusercontent.com/{owner}/{repo}/HEAD/README.md",
    ]


def save_memory(note: str) -> None:
    with db() as connection:
        connection.execute("INSERT INTO memories(note) VALUES (?)", (note[:40_000],))


def save_typed_memory(note: str, category: str = "general", project: str = "", source: str = "agent") -> None:
    allowed = {"preference", "project_fact", "procedure", "research", "task_history", "general"}
    category = category if category in allowed else "general"
    note = re.sub(r"\s+", " ", note).strip()
    with db() as connection:
        candidates = connection.execute(
            "SELECT note FROM memories WHERE COALESCE(category, 'general') = ? AND COALESCE(project, '') = ? AND COALESCE(source, 'user') = ?",
            (category, project[:200], source[:200]),
        ).fetchall()
        if any(re.sub(r"\s+", " ", row[0]).strip() == note[:40_000] for row in candidates):
            return
        connection.execute(
            "INSERT INTO memories(note, category, project, source) VALUES (?, ?, ?, ?)",
            (note[:40_000], category, project[:200], source[:200]),
        )


def job_event(job_id: str, message: str, **extra: Any) -> None:
    with RESEARCH_LOCK:
        job = RESEARCH_JOBS.get(job_id)
        if job is not None:
            job.setdefault("events", []).append({"time": time.time(), "message": message})
            job.update(extra)


def start_research_job(question: str, urls: list[str]) -> str:
    job_id = uuid.uuid4().hex
    artifact_dir = ROOT / ".job-artifacts" / job_id
    artifact_dir.mkdir(parents=True, exist_ok=True)
    with RESEARCH_LOCK:
        RESEARCH_JOBS[job_id] = {"status": "running", "events": [], "content": "", "question": question, "urls": urls, "cancel_requested": False, "artifact_dir": str(artifact_dir)}
    with db() as connection:
        connection.execute(
            "INSERT INTO job_records(job_id, kind, question, urls, status, artifact_dir) VALUES (?, ?, ?, ?, ?, ?)",
            (job_id, "research", question, json.dumps(urls, ensure_ascii=False), "running", str(artifact_dir)),
        )

    def worker():
        try:
            sources = []
            errors = []
            for index, url in enumerate(urls[:5], 1):
                with RESEARCH_LOCK:
                    cancelled = RESEARCH_JOBS.get(job_id, {}).get("cancel_requested")
                if cancelled:
                    job_event(job_id, "Araştırma kullanıcı tarafından iptal edildi.", status="cancelled")
                    return
                job_event(job_id, f"Kaynak {index}/{len(urls[:5])} okunuyor: {url}")
                try:
                    text = fetch_web_page(url)
                    sources.append(f"KAYNAK: {url}\n{text}")
                    job_event(job_id, f"Kaynak hazır: {url}")
                except Exception as exc:
                    errors.append(f"{url}: {exc}")
                    job_event(job_id, f"Kaynak okunamadı: {url}")
            if not sources:
                raise RuntimeError("Web kaynaklari okunamadi.")
            job_event(job_id, "Qwen kaynakları analiz ediyor...")
            prompt = (
                "Asagidaki web kaynaklarini kullanarak soruyu yanitla. Kaynaklarda olmayan bilgiyi uydurma. "
                "Yanitta hangi URL'den yararlandigini belirt.\n\n"
                f"SORU: {question}\n\n" + "\n\n".join(sources)
            )
            answer = call_ollama([{"role": "user", "content": prompt}])
            job_event(job_id, "Yanıt hazırlandı; kalıcı hafızaya yazılıyor...")
            save_memory(f"Web arastirma notu\nSoru: {question}\nKaynaklar: {', '.join(urls)}\n{answer}")
            (artifact_dir / "result.md").write_text(answer, encoding="utf-8")
            if errors:
                answer += "\n\nOkunamayan kaynaklar:\n" + "\n".join(errors)
            job_event(job_id, "Araştırma tamamlandı ve hafızaya kaydedildi.", status="completed", content=answer)
            with db() as connection:
                connection.execute("UPDATE job_records SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE job_id = ?", ("completed", job_id))
        except Exception as exc:
            (artifact_dir / "error.txt").write_text(str(exc), encoding="utf-8")
            job_event(job_id, f"Araştırma hatası: {exc}", status="failed", error=str(exc))
            with db() as connection:
                connection.execute("UPDATE job_records SET status = ?, error = ?, updated_at = CURRENT_TIMESTAMP WHERE job_id = ?", ("failed", str(exc), job_id))

    threading.Thread(target=worker, daemon=True).start()
    return job_id


def read_upload(upload: UploadFile) -> bytes:
    data = upload.file.read(-1 if MAX_UPLOAD_BYTES <= 0 else MAX_UPLOAD_BYTES + 1)
    if MAX_UPLOAD_BYTES > 0 and len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "Dosya boyutu siniri asildi.")
    return data


@app.get("/")
def index() -> FileResponse:
    return FileResponse(ROOT / "static" / "index.html")


@app.get("/api/status")
def status() -> dict[str, Any]:
    return {
        "model": OLLAMA_MODEL,
        "ollama": OLLAMA_BASE_URL,
        "workspace": str(WORKSPACE_ROOT),
        "memory_db": str(MEMORY_DB),
        "backup_root": str(AGENT_TOOLS.backup_root),
    }


def hardware_info() -> dict[str, Any]:
    total_ram = 0
    available_ram = 0
    if sys.platform == "win32":
        class MemoryStatus(ctypes.Structure):
            _fields_ = [("length", ctypes.c_ulong), ("memory_load", ctypes.c_ulong), ("total", ctypes.c_ulonglong), ("available", ctypes.c_ulonglong), ("total_page", ctypes.c_ulonglong), ("available_page", ctypes.c_ulonglong), ("total_virtual", ctypes.c_ulonglong), ("available_virtual", ctypes.c_ulonglong), ("available_extended", ctypes.c_ulonglong)]
        memory = MemoryStatus()
        memory.length = ctypes.sizeof(MemoryStatus)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(memory)):
            total_ram = memory.total
            available_ram = memory.available
    gpu = {"available": False, "name": "", "memory_mb": 0}
    nvidia = shutil.which("nvidia-smi")
    if nvidia:
        try:
            output = subprocess.check_output([nvidia, "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"], text=True, timeout=5).splitlines()[0]
            name, memory_mb = [part.strip() for part in output.split(",", 1)]
            gpu = {"available": True, "name": name, "memory_mb": int(memory_mb)}
        except (OSError, subprocess.SubprocessError, ValueError, IndexError):
            pass
    return {"ram_total_mb": total_ram // (1024 * 1024), "ram_available_mb": available_ram // (1024 * 1024), "gpu": gpu}


@app.get("/api/hardware")
def hardware() -> dict[str, Any]:
    return hardware_info()


def backend_health(name: str, url: str) -> dict[str, Any]:
    try:
        with urlopen(url, timeout=2) as response:
            return {"name": name, "available": 200 <= response.status < 500, "url": url}
    except (OSError, HTTPError, URLError):
        return {"name": name, "available": False, "url": url}


@app.get("/api/backends")
def backend_status() -> dict[str, Any]:
    backends = [
        backend_health("ollama", f"{OLLAMA_BASE_URL}/api/tags"),
        backend_health("local-agent-bridge", "http://127.0.0.1:8787/v1/models"),
        backend_health("ktransformers", "http://127.0.0.1:30000/health"),
    ]
    active = next((item["name"] for item in backends if item["available"]), "none")
    return {"order": ["ollama", "local-agent-bridge", "ktransformers"], "active": active, "backends": backends}


@app.get("/api/model-profiles")
def model_profiles() -> dict[str, Any]:
    hardware_state = hardware_info()
    fast_model = OLLAMA_CODE_MODEL
    if hardware_state["ram_available_mb"] and hardware_state["ram_available_mb"] < 4096:
        fast_model = "llama3.1:8b"
    safe_context = 4096
    if hardware_state["ram_available_mb"] >= 32768:
        safe_context = 16384
    elif hardware_state["ram_available_mb"] >= 8192:
        safe_context = 8192
    llama_root = ROOT / "AI-Runtimes" / "llama.cpp"
    llama_candidates = list(llama_root.rglob("llama-server.exe")) if llama_root.is_dir() else []
    llama_model_root = ROOT / "AI-Runtimes" / "models"
    llama_models = [
        path for path in llama_model_root.rglob("*.gguf")
        if path.is_file() and path.stat().st_size >= 100 * 1024 * 1024
    ] if llama_model_root.is_dir() else []
    profiles = {
        "fast": {"backend": "ollama", "model": fast_model, "purpose": "Kisa chat ve kod"},
        "reasoning": {"backend": "ollama", "model": OLLAMA_MODEL, "num_ctx": safe_context, "purpose": "Planlama ve uzun analiz"},
        "vision": {"backend": "ollama", "model": OLLAMA_MODEL, "num_ctx": safe_context, "purpose": "Gorsel analiz"},
        "llama_cpp": {"backend": "llama_cpp", "available": bool(llama_candidates and llama_models), "binary": str(llama_candidates[0]) if llama_candidates else "", "models": [str(path) for path in llama_models]},
    }
    ollama_models: list[str] = []
    try:
        tags = json.loads(urlopen(f"{OLLAMA_BASE_URL}/api/tags", timeout=3).read().decode("utf-8"))
        ollama_models = [str(item.get("name", "")) for item in tags.get("models", [])]
        ollama_available = bool(ollama_models)
    except (OSError, ValueError, HTTPError, URLError):
        ollama_available = False
    embedding_available = any(name == OLLAMA_EMBED_MODEL or name.split(":", 1)[0] == OLLAMA_EMBED_MODEL for name in ollama_models)
    return {"active_model": OLLAMA_MODEL, "hardware": hardware_state, "ollama_available": ollama_available, "ollama_models": ollama_models, "embedding_model": OLLAMA_EMBED_MODEL, "embedding_available": embedding_available, "profiles": profiles}


@app.get("/api/embedding/status")
def embedding_status() -> dict[str, Any]:
    profiles = model_profiles()
    available = profiles["embedding_available"]
    return {"model": OLLAMA_EMBED_MODEL, "available": available, "action": None if available else "ollama pull " + OLLAMA_EMBED_MODEL, "approval_required": not available}


@app.get("/api/ocr/status")
def ocr_status() -> dict[str, Any]:
    tesseract = find_tesseract()
    pytesseract_available = importlib.util.find_spec("pytesseract") is not None
    available = bool(tesseract and pytesseract_available)
    return {
        "available": available,
        "tesseract": tesseract or "",
        "pytesseract": pytesseract_available,
        "approval_required": not available,
        "actions": [] if available else ["python -m pip install pytesseract", "winget install --id UB-Mannheim.TesseractOCR -e"],
    }


@app.post("/api/ocr/prepare")
def prepare_ocr(request: EmbeddingInstallRequest) -> dict[str, Any]:
    status = ocr_status()
    if status["available"]:
        return {"status": "already_available", **status}
    if not request.approved:
        return {"status": "approval_required", **status}
    result = AGENT_TOOLS.run_approved([sys.executable, "-m", "pip", "install", "pytesseract"], approved=True)
    return {"status": "python_binding_installed", **status, "result": result}


@app.get("/api/setup/status")
def setup_status() -> dict[str, Any]:
    profiles = model_profiles()
    ocr = ocr_status()
    llama_model_root = ROOT / "AI-Runtimes" / "models"
    llama_model_ready = any(path.is_file() and path.stat().st_size >= 100 * 1024 * 1024 for path in llama_model_root.glob("*.gguf")) if llama_model_root.is_dir() else False
    dependency_check = subprocess.run(
        [sys.executable, "-m", "pip", "check"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    dependencies_ready = dependency_check.returncode == 0
    chromium_ready = (Path(os.getenv("LOCALAPPDATA", "")) / "ms-playwright").exists()
    commands = [
        {"name": "python_dependencies", "command": [sys.executable, "-m", "pip", "install", "-r", str(ROOT / "requirements.txt")], "needed": not dependencies_ready},
        {"name": "playwright_chromium", "command": [sys.executable, "-m", "playwright", "install", "chromium"], "needed": True},
        {"name": "qwen_model", "command": ["ollama", "pull", OLLAMA_MODEL], "needed": OLLAMA_MODEL not in profiles["ollama_models"]},
        {"name": "embedding_model", "command": ["ollama", "pull", OLLAMA_EMBED_MODEL], "needed": not profiles["embedding_available"]},
        {"name": "llama_cpp_model", "command": [sys.executable, str(ROOT / "download_llama_model.py")], "needed": not llama_model_ready},
        {"name": "ocr_python", "command": [sys.executable, "-m", "pip", "install", "pytesseract"], "needed": not ocr["pytesseract"]},
        {"name": "ocr_engine", "command": ["winget", "install", "--id", "UB-Mannheim.TesseractOCR", "-e"], "needed": not bool(ocr["tesseract"])},
    ]
    commands[1]["needed"] = not chromium_ready
    return {"ready": not any(item["needed"] for item in commands), "approval_required": True, "commands": commands, "dependency_check": dependencies_ready}


@app.post("/api/setup/prepare")
def prepare_setup(request: SetupRequest) -> dict[str, Any]:
    plan = setup_status()
    if not request.approved:
        return {"status": "approval_required", **plan}
    results = []
    for item in plan["commands"]:
        if not item["needed"]:
            continue
        result = AGENT_TOOLS.run_approved(item["command"], approved=True)
        results.append({"name": item["name"], **result})
        if not result.get("passed"):
            return {"status": "failed", "failed_step": item["name"], "results": results}
    return {"status": "completed", "results": results, "remaining": setup_status()["commands"]}


@app.post("/api/embedding/prepare")
def prepare_embedding(request: EmbeddingInstallRequest) -> dict[str, Any]:
    status = embedding_status()
    if status["available"]:
        return {"status": "already_available", **status}
    if not request.approved:
        return {"status": "approval_required", **status}
    result = AGENT_TOOLS.run_approved(["ollama", "pull", OLLAMA_EMBED_MODEL], approved=True)
    return {"status": "completed", **status, "result": result}


@app.post("/api/model-profiles/select")
def select_model_profile(request: ModelProfileRequest) -> dict[str, Any]:
    profiles = model_profiles()["profiles"]
    profile = profiles.get(request.profile)
    if profile is None:
        raise HTTPException(404, "Model profili bulunamadi.")
    if profile.get("backend") == "llama_cpp" and not profile.get("available"):
        raise HTTPException(503, "llama.cpp runtime bulunamadi; Ollama profilleri kullanilabilir.")
    return {"status": "available", "profile": request.profile, **profile}


@app.get("/api/memory/export")
def export_memory() -> dict[str, Any]:
    with db() as connection:
        memories = connection.execute(
            "SELECT id, note, category, project, source, created_at FROM memories ORDER BY id"
        ).fetchall()
        operations = connection.execute(
            "SELECT id, operation, reasoning, result, created_at FROM operation_journal ORDER BY id"
        ).fetchall()
    unique_memories = []
    seen_memories: set[tuple[str, str, str, str]] = set()
    for row in memories:
        item = dict(zip(("id", "note", "category", "project", "source", "created_at"), row))
        key = (
            re.sub(r"\s+", " ", item["note"]).strip(),
            item.get("category") or "general",
            item.get("project") or "",
            item.get("source") or "user",
        )
        if key not in seen_memories:
            seen_memories.add(key)
            item["note"] = key[0]
            unique_memories.append(item)
    return {
        "format": "localqwen-memory-v1",
        "exported_at": datetime.now().isoformat(timespec="seconds"),
        "memories": unique_memories,
        "operations": [dict(zip(("id", "operation", "reasoning", "result", "created_at"), row)) for row in operations],
    }


class MemoryImportRequest(BaseModel):
    payload: dict[str, Any]


@app.post("/api/memory/import")
def import_memory(request: MemoryImportRequest) -> dict[str, int]:
    memories = request.payload.get("memories", [])
    operations = request.payload.get("operations", [])
    imported_memories = 0
    imported_operations = 0
    with db() as connection:
        for item in memories:
            if not isinstance(item, dict) or not str(item.get("note", "")).strip():
                continue
            note = re.sub(r"\s+", " ", str(item["note"])).strip()[:40_000]
            category = str(item.get("category") or "general")
            project = str(item.get("project") or "")[:200]
            source = str(item.get("source") or "user")[:200]
            candidates = connection.execute(
                "SELECT note, category, project, source FROM memories"
            ).fetchall()
            duplicate = any(
                (
                    re.sub(r"\s+", " ", row[0]).strip(),
                    "general" if row[1] in (None, "", "None") else str(row[1]),
                    "" if row[2] in (None, "", "None") else str(row[2]),
                    "user" if row[3] in (None, "", "None") else str(row[3]),
                ) == (note, category, project, source)
                for row in candidates
            )
            if not duplicate:
                connection.execute(
                    "INSERT INTO memories(note, category, project, source) VALUES (?, ?, ?, ?)",
                    (note, category, project, source),
                )
                imported_memories += 1
        for item in operations:
            if not isinstance(item, dict) or not str(item.get("operation", "")).strip():
                continue
            operation = str(item.get("operation", ""))[:500]
            reasoning = str(item.get("reasoning", ""))[:4000]
            result = str(item.get("result", ""))[:12000]
            duplicate = connection.execute(
                "SELECT 1 FROM operation_journal WHERE operation = ? AND reasoning = ? AND result = ? LIMIT 1",
                (operation, reasoning, result),
            ).fetchone()
            if not duplicate:
                connection.execute(
                    "INSERT INTO operation_journal(operation, reasoning, result) VALUES (?, ?, ?)",
                    (operation, reasoning, result),
                )
                imported_operations += 1
    return {"imported_memories": imported_memories, "imported_operations": imported_operations}


def memory_source_preview(source: str) -> dict[str, Any]:
    source = source.strip()
    with db() as connection:
        rows = connection.execute(
            "SELECT id, note, category, project, source, created_at FROM memories WHERE source = ? ORDER BY id",
            (source,),
        ).fetchall()
        preview = [dict(zip(("id", "note", "category", "project", "source", "created_at"), row)) for row in rows]
    return {"status": "confirmation_required", "source": source, "count": len(preview), "memories": preview[:20]}


@app.get("/api/memory/source")
def preview_memory_by_source(source: str = Query(..., min_length=1, max_length=200)) -> dict[str, Any]:
    return memory_source_preview(source)


@app.delete("/api/memory/source")
def delete_memory_by_source(
    source: str = Query(..., min_length=1, max_length=200),
    confirm: bool = Query(False),
) -> dict[str, Any]:
    source = source.strip()
    if not confirm:
        return memory_source_preview(source)
    with db() as connection:
        rows = connection.execute(
            "SELECT id, note, category, project, source, created_at FROM memories WHERE source = ? ORDER BY id",
            (source,),
        ).fetchall()
        preview = [dict(zip(("id", "note", "category", "project", "source", "created_at"), row)) for row in rows]
        backup = ROOT / ".memory-delete-backups" / f"{int(time.time())}-{uuid.uuid4().hex}.json"
        backup.parent.mkdir(parents=True, exist_ok=True)
        backup.write_text(json.dumps(preview, ensure_ascii=False, indent=2), encoding="utf-8")
        connection.execute("DELETE FROM memories WHERE source = ?", (source,))
    journal_operation("memory_delete", "Kullanici kaynak bazli hafiza silmeyi onayladi.", json.dumps({"source": source, "count": len(preview), "backup": str(backup)}, ensure_ascii=False))
    return {"status": "deleted", "source": source, "count": len(preview), "backup": str(backup)}


@app.get("/api/memory")
def list_memory() -> dict[str, Any]:
    with db() as connection:
        memories = connection.execute(
            "SELECT id, note, category, project, source, created_at FROM memories ORDER BY id DESC LIMIT 100"
        ).fetchall()
        operations = connection.execute(
            "SELECT id, operation, reasoning, result, created_at FROM operation_journal ORDER BY id DESC LIMIT 100"
        ).fetchall()
    return {
        "memory_db": str(MEMORY_DB),
        "memories": [dict(zip(("id", "note", "category", "project", "source", "created_at"), row)) for row in memories],
        "operations": [
            dict(zip(("id", "operation", "reasoning", "result", "created_at"), row))
            for row in operations
        ],
    }


@app.get("/api/memory/search")
def search_memory(
    q: str = Query("", max_length=500),
    project: str = Query("", max_length=200),
    source: str = Query("", max_length=200),
    category: str = Query("", max_length=50),
    since: str = Query("", max_length=32),
    until: str = Query("", max_length=32),
    limit: int = Query(50, ge=1, le=200),
) -> dict[str, Any]:
    clauses = []
    values: list[Any] = []
    if q.strip():
        clauses.append("note LIKE ?")
        values.append(f"%{q.strip()}%")
    if project.strip():
        clauses.append("project LIKE ?")
        values.append(f"%{project.strip()}%")
    if source.strip():
        clauses.append("source LIKE ?")
        values.append(f"%{source.strip()}%")
    if category.strip():
        clauses.append("category = ?")
        values.append(category.strip())
    if since.strip():
        clauses.append("created_at >= ?")
        values.append(since.strip())
    if until.strip():
        clauses.append("created_at <= ?")
        values.append(until.strip())
    where = " WHERE " + " AND ".join(clauses) if clauses else ""
    with db() as connection:
        rows = connection.execute(
            f"SELECT id, note, category, project, source, created_at FROM memories{where} ORDER BY id DESC LIMIT ?",
            [*values, limit],
        ).fetchall()
    return {
        "query": {"q": q, "project": project, "source": source, "category": category, "since": since, "until": until},
        "count": len(rows),
        "memories": [dict(zip(("id", "note", "category", "project", "source", "created_at"), row)) for row in rows],
    }


@app.get("/api/memory/rag-context")
def memory_rag_context(q: str = Query(..., min_length=1, max_length=500), limit: int = Query(8, ge=1, le=30)) -> dict[str, Any]:
    context = retrieved_memory_context(q, limit)
    return {"query": q, "retrieval": "sqlite-keyword", "context": context, "count": len(context.splitlines()) if context else 0}


@app.get("/api/memory/semantic-search")
def semantic_memory_search(q: str = Query(..., min_length=1, max_length=500), limit: int = Query(8, ge=1, le=30)) -> dict[str, Any]:
    with db() as connection:
        rows = connection.execute(
            "SELECT id, note, category, project, source, created_at FROM memories ORDER BY id DESC LIMIT 200"
        ).fetchall()
    if not rows:
        return {"query": q, "retrieval": "embedding", "count": 0, "memories": []}
    try:
        vectors = ollama_embed([q] + [row[1] for row in rows])
    except (HTTPError, URLError, OSError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(503, f"Embedding modeli kullanilamiyor ({OLLAMA_EMBED_MODEL}). Kurulum icin onay bekleniyor: ollama pull {OLLAMA_EMBED_MODEL}") from exc
    query_vector = vectors[0]
    scored = sorted(
        ((cosine_similarity(query_vector, vector), row) for vector, row in zip(vectors[1:], rows)),
        key=lambda item: item[0], reverse=True,
    )[:limit]
    fields = ("id", "note", "category", "project", "source", "created_at")
    return {"query": q, "retrieval": "embedding", "embedding_model": OLLAMA_EMBED_MODEL, "count": len(scored), "memories": [{**dict(zip(fields, row)), "score": score} for score, row in scored]}


@app.get("/v1/models")
def openai_models() -> dict[str, Any]:
    return {
        "object": "list",
        "data": [{"id": "local-qwen", "object": "model", "owned_by": "LocalQwenAgent"}],
    }


@app.post("/v1/chat/completions")
def openai_chat(request: OpenAIChatRequest) -> dict[str, Any]:
    messages = [
        {"role": item.get("role", "user"), "content": str(item.get("content", ""))}
        for item in request.messages
        if item.get("role") in {"system", "user", "assistant"}
        and str(item.get("content", "")).strip()
    ]
    if not messages:
        raise HTTPException(400, "En az bir gecerli mesaj gerekli.")
    content = call_ollama(messages, model=CONTINUE_MODEL, num_predict=request.max_tokens)
    user_message = next(
        (item["content"] for item in reversed(messages) if item["role"] == "user"),
        "",
    )
    journal_operation(
        "v1_chat",
        "VS Code uyumlu yerel kopru istegi Ollama'ya yonlendirildi.",
        json.dumps(
            {"model": request.model, "message_length": len(user_message), "status": "completed"},
            ensure_ascii=False,
        ),
    )
    created = int(time.time())
    return {
        "id": f"chatcmpl-local-{uuid.uuid4().hex}",
        "object": "chat.completion",
        "created": created,
        "model": request.model,
        "choices": [{
            "index": 0,
            "message": {"role": "assistant", "content": content},
            "finish_reason": "stop",
        }],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    }


@app.post("/api/agent/plan")
def agent_plan(request: AgentPlanRequest) -> dict[str, Any]:
    decision = decide(request.message)
    task_id = uuid.uuid4().hex
    steps = plan_for(request.message)
    result = {
        "task_id": task_id,
        "intent": decision.intent,
        "steps": steps,
        "approval_required": decision.needs_tool_approval,
        "approved": request.approved,
        "status": "ready_to_execute" if request.approved else "plan_only",
    }
    with db() as connection:
        connection.execute(
            "INSERT INTO task_records(task_id, request, intent, plan, approved, status) VALUES (?, ?, ?, ?, ?, ?)",
            (task_id, request.message, decision.intent, json.dumps(steps, ensure_ascii=False), int(request.approved), result["status"]),
        )
    journal_operation("plan", decision.instructions, json.dumps(result, ensure_ascii=False))
    return result


@app.get("/api/agent/tasks")
def agent_tasks() -> dict[str, Any]:
    with db() as connection:
        rows = connection.execute(
            "SELECT task_id, request, intent, plan, approved, status, commands, changed_files, tests, result, created_at, updated_at FROM task_records ORDER BY created_at DESC LIMIT 100"
        ).fetchall()
    fields = ("task_id", "request", "intent", "plan", "approved", "status", "commands", "changed_files", "tests", "result", "created_at", "updated_at")
    return {"tasks": [dict(zip(fields, row)) for row in rows]}


@app.post("/api/agent/file")
def agent_file_workflow(request: FileWorkflowRequest) -> dict[str, Any]:
    if request.action == "read":
        return {"status": "read", **AGENT_TOOLS.read_file(request.path)}
    if request.action != "write":
        raise HTTPException(400, "Dosya islemi read veya write olmali.")
    preview = AGENT_TOOLS.preview_write(request.path, request.content)
    if not request.approved:
        return {"status": "approval_required", "preview": preview}
    result = AGENT_TOOLS.write_file(request.path, request.content)
    verified = AGENT_TOOLS.read_file(request.path)
    journal_operation("file_workflow", "Kullanici dosya yazma islemini onayladi.", json.dumps({"path": request.path, "verified": verified["content"] == request.content}, ensure_ascii=False))
    return {"status": "written", "result": result, "verified": verified["content"] == request.content}


@app.get("/api/agent/profiles")
def agent_profiles() -> dict[str, Any]:
    profiles: list[dict[str, Any]] = []
    requirements = ROOT / "requirements.txt"
    if requirements.exists():
        profiles.append({
            "name": "dependencies",
            "detected": True,
            "actions": {
                "check": [sys.executable, "-m", "pip", "check"],
                "install": [sys.executable, "-m", "pip", "install", "-r", str(requirements)],
            },
        })
    if (WORKSPACE_ROOT / "pyproject.toml").exists() or list(WORKSPACE_ROOT.glob("*.py")):
        agent_test = WORKSPACE_ROOT / "Yapay Zeka" / "test_agent.py"
        if not agent_test.exists():
            agent_test = WORKSPACE_ROOT / "test_agent.py"
        test_command = [sys.executable, "-m", "pytest", "-q"]
        if agent_test.exists():
            test_command.append(str(agent_test.relative_to(WORKSPACE_ROOT)))
        else:
            test_command.extend(["--ignore=AI-Runtimes", "--ignore=DeepPanda/DeepPanda-App/tools"])
        profiles.append({
            "name": "python",
            "detected": True,
            "actions": {
                "test": test_command,
                "compile": [sys.executable, "-m", "compileall", "-q", str(ROOT)],
                "lint": ["ruff", "check", str(ROOT)],
            },
        })
    if (WORKSPACE_ROOT / "package.json").exists():
        profiles.append({
            "name": "node",
            "detected": True,
            "actions": {
                "test": ["npm", "test"],
                "build": ["npm", "run", "build"],
                "lint": ["npm", "run", "lint"],
            },
        })
    if (WORKSPACE_ROOT / "DeepPanda").exists() or WORKSPACE_ROOT.name.lower().startswith("deeppanda"):
        profiles.append({
            "name": "deeppanda",
            "detected": True,
            "actions": {
                "test": [sys.executable, "-m", "pytest", "-q", "--ignore=AI-Runtimes", "--ignore=DeepPanda/DeepPanda-App/tools"],
                "compile": [sys.executable, "-m", "compileall", "DeepPanda"],
            },
        })
    return {"workspace": str(WORKSPACE_ROOT), "profiles": profiles}


@app.post("/api/agent/profile/execute")
def agent_profile_execute(request: AgentProfileExecuteRequest) -> dict[str, Any]:
    profiles = agent_profiles()["profiles"]
    profile = next((item for item in profiles if item["name"] == request.profile), None)
    if profile is None or request.action not in profile["actions"]:
        raise HTTPException(404, "Profil veya profil islemi bulunamadi.")
    command = profile["actions"][request.action]
    if not request.approved:
        return {"status": "approval_required", "profile": request.profile, "action": request.action, "command": command}
    result = AGENT_TOOLS.run_approved(command, approved=True)
    journal_operation("profile_command", f"Profil={request.profile}, islem={request.action}", json.dumps(result, ensure_ascii=False))
    return {"profile": request.profile, "action": request.action, "command": command, **result}


@app.post("/api/agent/execute")
def agent_execute(request: AgentExecuteRequest) -> dict[str, Any]:
    if not request.approved:
        update_task(request.task_id, status="approval_required", commands=json.dumps(request.command, ensure_ascii=False))
        return {"status": "approval_required", "command": request.command}
    result = AGENT_TOOLS.run_approved(request.command, approved=True)
    update_task(
        request.task_id,
        approved=1,
        status=result.get("status", "completed"),
        commands=json.dumps(request.command, ensure_ascii=False),
        result=json.dumps(result, ensure_ascii=False),
    )
    journal_operation("command", "Kullanici acik onay verdi.", json.dumps(result, ensure_ascii=False))
    save_memory(f"Agent komut sonucu\nKomut: {' '.join(request.command)}\nDurum: {result.get('status')}\nKod: {result.get('returncode')}")
    return result


@app.post("/api/agent/generate")
def agent_generate(request: AgentGenerateRequest) -> dict[str, Any]:
    context = workspace_context(request.request)
    prompt = (
        "Bir yazilim agenti olarak kullanici istegi icin dosya plani ve kod uret. "
        "Yalnizca JSON don: {\"summary\": string, \"files\": [{\"path\": string, \"content\": string}], \"tests\": [string]}. "
        "Dosya yollari workspace goreli olsun. Tehlikeli veya workspace disi islem uretme. "
        "Mevcut baglami koru ve test edilebilir kod yaz.\n\n"
        f"ISTEK: {request.request}\nPROJE YOLU: {request.project_path}\nMEVCUT BAGLAM:\n{context or 'Yok'}"
    )
    generated = extract_json_object(
        call_ollama(
            [{"role": "user", "content": prompt}],
            json_format=True,
            model=OLLAMA_CODE_MODEL,
            num_ctx=8192,
            num_predict=4096,
            timeout=300,
        )
    )
    files = generated.get("files", [])
    if not isinstance(files, list) or any(
        not isinstance(item, dict) or not isinstance(item.get("path"), str) or not isinstance(item.get("content"), str)
        for item in files
    ):
        raise HTTPException(502, "Model dosya planinda path/content eksik.")
    wants_project = any(word in request.request.lower() for word in ("proje", "oyun", "uygulama", "program", "kütüphane", "kutuphane"))
    if wants_project and len(files) < 2:
        repair_prompt = (
            "Onceki kod uretimi eksik kaldi. Kullanici istegi icin dosyalari tamamla. "
            "Yalnizca JSON don: {\"summary\": string, \"files\": [{\"path\": string, \"content\": string}], \"tests\": [string]}. "
            "En az bir ana kaynak, bir test dosyasi ve README.md uret."
            f"\nISTEK: {request.request}\nONCEKI DOSYALAR: {json.dumps(files, ensure_ascii=False)}"
        )
        repaired = extract_json_object(
            call_ollama(
                [{"role": "user", "content": repair_prompt}],
                json_format=True,
                model=OLLAMA_CODE_MODEL,
                num_ctx=8192,
                num_predict=4096,
                timeout=300,
            )
        )
        repaired_files = repaired.get("files", [])
        if isinstance(repaired_files, list) and repaired_files:
            generated = repaired
    return generated


@app.post("/api/agent/apply")
def agent_apply(request: AgentApplyRequest) -> dict[str, Any]:
    if not request.files:
        raise HTTPException(400, "Uygulanacak dosya bulunamadi.")
    if not request.approved:
        previews = [
            AGENT_TOOLS.preview_write(item["path"], item["content"])
            for item in request.files
        ]
        return {"status": "approval_required", "previews": previews}
    results = []
    for item in request.files:
        results.append(AGENT_TOOLS.write_file(item["path"], item["content"]))
    update_task(
        request.task_id,
        approved=1,
        status="completed",
        changed_files=json.dumps([item["path"] for item in results], ensure_ascii=False),
        result=json.dumps(results, ensure_ascii=False),
    )
    journal_operation("file_apply", "Kullanici acik onay verdi; workspace backup uygulandi.", f"{len(results)} dosya")
    save_memory(f"Agent dosya uygulama sonucu: {len(results)} dosya yazildi.")
    return {"status": "applied", "files": results}


@app.post("/api/agent/rollback")
def agent_rollback(request: AgentRollbackRequest) -> dict[str, Any]:
    with db() as connection:
        row = connection.execute(
            "SELECT result, status FROM task_records WHERE task_id = ?",
            (request.task_id,),
        ).fetchone()
    if row is None:
        raise HTTPException(404, "Task bulunamadi.")
    result_text, status = row
    if status != "completed":
        raise HTTPException(409, "Yalnizca tamamlanmis task geri alinabilir.")
    try:
        results = json.loads(result_text)
    except json.JSONDecodeError as exc:
        raise HTTPException(500, "Task sonucu gecersiz.") from exc
    if not isinstance(results, list) or not results:
        raise HTTPException(409, "Task geri alinabilir dosya sonucu icermiyor.")
    rolled_back = [AGENT_TOOLS.rollback_write(item) for item in results]
    update_task(request.task_id, status="rolled_back", result=json.dumps(rolled_back, ensure_ascii=False))
    journal_operation("rollback", "Kullanici task geri alma istedi.", json.dumps(rolled_back, ensure_ascii=False))
    return {"status": "rolled_back", "files": rolled_back}


@app.post("/api/agent/self-audit")
def agent_self_audit(request: SelfAuditRequest) -> dict[str, Any]:
    python_files = sorted(
        path for path in ROOT.glob("*.py") if path.name != "memory.db"
    )
    compile_result = subprocess.run(
        [sys.executable, "-m", "py_compile", *(str(path) for path in python_files)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    test_result: subprocess.CompletedProcess[str] | None = None
    if request.run_tests:
        test_result = subprocess.run(
            [sys.executable, "-m", "pytest", "test_agent.py", "-q"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )
    result = {
        "status": "passed" if compile_result.returncode == 0 and (test_result is None or test_result.returncode == 0) else "failed",
        "python_files": [path.name for path in python_files],
        "compile_returncode": compile_result.returncode,
        "compile_output": (compile_result.stdout + compile_result.stderr)[-4000:],
        "tests_returncode": None if test_result is None else test_result.returncode,
        "tests_output": None if test_result is None else (test_result.stdout + test_result.stderr)[-4000:],
    }
    learning = (
        "Self-audit yerel olarak tamamlandi: "
        f"{len(python_files)} Python dosyasi derlendi; "
        f"compile={compile_result.returncode}; "
        f"tests={None if test_result is None else test_result.returncode}."
    )
    journal_operation("self_audit", "Agent kendi workspace kodunu ve testlerini kontrol etti.", json.dumps(result, ensure_ascii=False))
    save_memory(learning)
    return result


@app.post("/api/chat")
def chat(request: ChatRequest) -> dict[str, str]:
    message = request.message.strip()
    if not message:
        raise HTTPException(400, "Mesaj bos olamaz.")
    if re.fullmatch(r"(?:merhaba|merhabalar|selam|selamlar|hey|hi|hello)[!. ]*", message, re.IGNORECASE):
        return {"content": "Merhaba! Nasıl yardımcı olabilirim?", "intent": "greeting"}
    if any(marker in message.lower() for marker in ("nereye kayıt", "nereye kayit", "hafıza nerede", "hafiza nerede")):
        return {
            "content": (
                f"Kalıcı notlar: {MEMORY_DB}\n"
                f"İşlem günlüğü: {MEMORY_DB} içindeki operation_journal tablosu\n"
                f"Dosya yedekleri: {AGENT_TOOLS.backup_root}\n"
                "Taşımak için memory.db dosyasını ve gerekirse .localqwen-backups klasörünü kopyalayabilirsin."
            ),
            "intent": "memory_location",
        }
    if any(marker in message.lower() for marker in ("neler yapabilirsin", "neler yapabilir", "ne yapabilirsin", "yeteneklerin")):
        return {
            "content": (
                "Ben DeepPanda icindeki yerel LocalQwenAgent'im.\n\n"
                "Yapabildiklerim:\n"
                "- DeepPanda workspace icindeki dosyalari okuyabilirim.\n"
                "- Onayindan sonra dosya olusturabilir veya degistirebilirim; mevcut dosyalari once yedeklerim.\n"
                "- Python, test, compile ve izinli yerel komutlari calistirabilirim; sonucu operation_journal'a kaydederim.\n"
                "- Notlari, arastirma sonuclarini ve islemleri memory.db icindeki kalici hafizaya kaydedebilirim.\n"
                "- PDF, metin, gorsel, ses/video ve public web/GitHub kaynaklarini analiz edebilirim.\n"
                "- Proje plani, kod, test ve dosya degisikligi uretebilirim.\n\n"
                "Sinirlarim: workspace disina yazamam, onaysiz komut veya dosya degisikligi yapmam, gizli ic dusunme taslagimi gostermem."
            ),
            "intent": "capabilities",
        }
    decision = decide(message)
    context_parts = []
    if request.memory:
        context_parts.append("Retrieved kalici hafiza:\n" + (retrieved_memory_context(message) or "Yok"))
        context_parts.append("Onceki operasyonlar:\n" + (operation_context() or "Yok"))
    context_parts.append("Workspace baglami:\n" + (workspace_context(message) or "Yok"))
    system = system_prompt(decision, "\n\n".join(context_parts))
    if any(marker in message.lower() for marker in ("ayrıntı", "ayrinti", "detay", "adım adım", "adim adim", "nedenini")):
        system += "\nKullanici ayrinti istedi: sonucu, gerekceleri, varsayimlari ve uygulanabilir adimlari ayrintili anlat; gizli ic dusunme taslagini yazma."
    answer = call_ollama([{"role": "system", "content": system}, {"role": "user", "content": message}])
    wants_learning = any(
        marker in message.lower()
        for marker in ("öğren", "ogren", "hafızaya", "hafizaya", "kalıcı", "kalici", "kaydet")
    )
    result = {"content": answer, "intent": decision.intent}
    if wants_learning:
        learning_note = f"Kullanici tarafindan kaydedilen ogrenme notu\nSoru: {message}\nYanıt: {answer}"
        if REQUIRE_MEMORY_APPROVAL and not request.approve_memory:
            result["memory_pending"] = learning_note
            result["memory"] = "Öğrenme notu hazır; kalıcı hafızaya kaydetmek için onay gerekli."
        else:
            save_typed_memory(learning_note, "research", str(WORKSPACE_ROOT), "chat")
            result["memory"] = "Öğrenilen bilgi kalıcı hafızaya kaydedildi."
    return result


@app.post("/api/research")
def research(request: ResearchRequest) -> dict[str, str]:
    question = request.question.strip()
    urls = [url.strip() for url in request.urls if url.strip()][:5]
    if not question or not urls:
        raise HTTPException(400, "Soru ve en az bir URL gerekli.")
    sources = []
    errors = []
    for url in urls:
        try:
            text = fetch_web_page(url)
            sources.append(f"KAYNAK: {url}\n{text}")
        except Exception as exc:
            errors.append(f"{url}: {exc}")
    if not sources:
        raise HTTPException(502, "Web kaynaklari okunamadi: " + "; ".join(errors))
    prompt = (
        "Asagidaki web kaynaklarini kullanarak soruyu yanitla. Kaynaklarda olmayan bilgiyi uydurma. "
        "Yanitta hangi URL'den yararlandigini belirt.\n\n"
        f"SORU: {question}\n\n" + "\n\n".join(sources)
    )
    answer = call_ollama([{"role": "user", "content": prompt}])
    save_memory(f"Web arastirma notu\nSoru: {question}\nKaynaklar: {', '.join(urls)}\n{answer}")
    if errors:
        answer += "\n\nOkunamayan kaynaklar:\n" + "\n".join(errors)
    return {"content": answer}


@app.post("/api/research/start")
def research_start(request: ResearchRequest) -> dict[str, str]:
    question = request.question.strip()
    urls = [url.strip() for url in request.urls if url.strip()]
    if not question or not urls:
        raise HTTPException(400, "Soru ve en az bir URL gerekli.")
    return {"job_id": start_research_job(question, urls)}


@app.get("/api/research/jobs/{job_id}")
def research_job(job_id: str) -> dict[str, Any]:
    with RESEARCH_LOCK:
        job = RESEARCH_JOBS.get(job_id)
        if job is None:
            raise HTTPException(404, "Araştırma işi bulunamadı.")
        return {**job, "events": list(job.get("events", []))}


@app.get("/api/research/jobs")
def research_jobs() -> dict[str, Any]:
    with db() as connection:
        rows = connection.execute(
            "SELECT job_id, kind, question, urls, status, artifact_dir, error, created_at, updated_at FROM job_records ORDER BY created_at DESC LIMIT 100"
        ).fetchall()
    fields = ("job_id", "kind", "question", "urls", "status", "artifact_dir", "error", "created_at", "updated_at")
    return {"jobs": [dict(zip(fields, row)) for row in rows]}


@app.post("/api/research/jobs/{job_id}/cancel")
def cancel_research_job(job_id: str) -> dict[str, str]:
    with RESEARCH_LOCK:
        job = RESEARCH_JOBS.get(job_id)
        if job is None:
            raise HTTPException(404, "Araştırma işi bulunamadı.")
        if job.get("status") not in {"running"}:
            return {"status": str(job.get("status"))}
        job["cancel_requested"] = True
        job.setdefault("events", []).append({"time": time.time(), "message": "İptal istendi."})
    with db() as connection:
        connection.execute("UPDATE job_records SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE job_id = ?", ("cancel_requested", job_id))
    return {"status": "cancel_requested"}


@app.post("/api/research/jobs/{job_id}/retry")
def retry_research_job(job_id: str) -> dict[str, str]:
    with RESEARCH_LOCK:
        job = RESEARCH_JOBS.get(job_id)
        if job is None:
            raise HTTPException(404, "Araştırma işi bulunamadı.")
        if job.get("status") not in {"failed", "cancelled"}:
            raise HTTPException(409, "Yalnızca başarısız veya iptal edilmiş işler tekrarlanabilir.")
        question = str(job.get("question", ""))
        urls = list(job.get("urls", []))
    return {"job_id": start_research_job(question, urls)}


@app.post("/api/browser/snapshot")
async def browser_snapshot(request: BrowserRequest) -> dict[str, str]:
    """Render a public page with Chromium without executing local actions."""
    parsed = urlparse(request.url.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise HTTPException(400, "Yalnizca public http/https URL kullanilabilir.")
    try:
        from playwright.async_api import async_playwright
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(request.url, wait_until="domcontentloaded", timeout=30_000)
            title = await page.title()
            text = (await page.locator("body").inner_text())[:40_000]
            await browser.close()
        return {"title": title, "content": text}
    except ImportError as exc:
        raise HTTPException(503, "Playwright kurulu degil.") from exc
    except Exception as exc:
        raise HTTPException(502, f"Browser sayfasi okunamadi: {exc}") from exc


@app.post("/api/github/research")
def github_research(request: GitHubResearchRequest) -> dict[str, str]:
    question = request.question.strip()
    repositories = [item.strip() for item in request.repositories if item.strip()][:3]
    if not question or not repositories:
        raise HTTPException(400, "Soru ve en az bir GitHub repository URL'si gerekli.")

    sources: list[str] = []
    errors: list[str] = []
    for repository in repositories:
        try:
            for source_url in github_sources(repository):
                try:
                    text = fetch_web_page(source_url)
                    if text.strip():
                        sources.append(f"KAYNAK: {source_url}\n{text}")
                except Exception as exc:
                    errors.append(f"{source_url}: {exc}")
        except Exception as exc:
            errors.append(f"{repository}: {exc}")
    if not sources:
        raise HTTPException(502, "GitHub kaynaklari okunamadi: " + "; ".join(errors))

    prompt = (
        "GitHub kaynaklarini incele ve soruya cevap ver. Ardindan 'OGRENME NOTU' basligi altinda "
        "projenin mimarisini, kurulumunu, onemli kurallarini ve gelecekte hatirlanmasi gerekenleri "
        "kisa maddelerle yaz. Kaynaklarda olmayan detaylari uydurma. Kaynak URL'lerini belirt.\n\n"
        f"SORU: {question}\n\n" + "\n\n".join(sources)
    )
    answer = call_ollama([{"role": "user", "content": prompt}])
    note = f"GitHub ogrenme notu\nSoru: {question}\nKaynaklar: {', '.join(repositories)}\n{answer}"
    save_memory(note)
    if errors:
        answer += "\n\nOkunamayan kaynaklar:\n" + "\n".join(errors)
    return {"content": answer, "memory": "GitHub ogrenme notu kalici hafizaya kaydedildi."}


@app.post("/api/tools/run")
def run_tool(request: ToolRequest) -> dict[str, object]:
    """Run only an approved, workspace-scoped tool command."""
    try:
        return AGENT_TOOLS.run_approved(request.command, request.approved)
    except subprocess.TimeoutExpired as exc:
        raise HTTPException(408, "Arac islemi zaman asimina ugradi.") from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@app.get("/api/tools/file")
def read_tool_file(path: str) -> dict[str, str]:
    if AGENT_DEV_MODE != "workspace":
        raise HTTPException(403, "Workspace gelistirme modu kapali.")
    try:
        target = AGENT_TOOLS.safe_path(path)
        if not target.is_file() or target.stat().st_size > 2_000_000:
            raise ValueError("Dosya yok veya boyutu cok buyuk.")
        return {"path": str(target), "content": target.read_text(encoding="utf-8", errors="replace")}
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@app.post("/api/tools/file")
def write_tool_file(request: FileWriteRequest) -> dict[str, str]:
    if AGENT_DEV_MODE != "workspace":
        raise HTTPException(403, "Workspace gelistirme modu kapali.")
    try:
        return AGENT_TOOLS.write_file(request.path, request.content)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@app.post("/api/media/analyze")
async def analyze_media(file: UploadFile = File(...), transcribe: bool = Form(True)) -> dict[str, Any]:
    """Extract bounded media evidence; transcription is optional and local."""
    data = read_upload(file)
    suffix = Path(file.filename or "media").suffix.lower()
    if suffix not in {".mp4", ".mov", ".mkv", ".avi", ".wav", ".mp3", ".m4a", ".webm"}:
        raise HTTPException(400, "Video veya ses dosyasi gerekli.")
    media_dir = ROOT / ".media-work" / uuid.uuid4().hex
    media_dir.mkdir(parents=True, exist_ok=True)
    source = media_dir / f"input{suffix}"
    source.write_bytes(data)
    audio = media_dir / "audio.wav"
    frames = media_dir / "frame-%03d.jpg"
    result: dict[str, Any] = {"filename": file.filename, "frames": [], "transcript": ""}
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-i", str(source), "-vn", "-ac", "1", "-ar", "16000", str(audio)],
            check=True, capture_output=True, text=True, timeout=300,
        )
        subprocess.run(
            ["ffmpeg", "-y", "-i", str(source), "-vf", "fps=1/10", "-frames:v", "12", str(frames)],
            check=True, capture_output=True, text=True, timeout=300,
        )
        frame_paths = sorted(media_dir.glob("frame-*.jpg"))
        result["frames"] = [
            {"path": str(path), "timestamp_seconds": index * 10}
            for index, path in enumerate(frame_paths)
        ]
        result["vision_observations"] = []
        if transcribe:
            try:
                from faster_whisper import WhisperModel
                model = WhisperModel("small", device="cpu", compute_type="int8")
                segments, _info = model.transcribe(str(audio))
                result["transcript"] = " ".join(segment.text.strip() for segment in segments)
            except ImportError:
                result["transcript"] = "faster-whisper kurulu degil; transkripsiyon atlandi."
        for frame in frame_paths[:3]:
            try:
                observation = call_ollama_vision(
                    frame.read_bytes(),
                    "Bu video karesini kanita dayali ve kisa analiz et. Gorunen nesneleri, metni, ekran durumunu ve belirsizlikleri belirt.",
                    ".jpg",
                )
                result["vision_observations"].append({"timestamp_seconds": frame_paths.index(frame) * 10, "content": observation})
            except HTTPException as exc:
                result["vision_observations"].append({"timestamp_seconds": frame_paths.index(frame) * 10, "error": str(exc.detail)})
        result["report"] = {
            "filename": file.filename,
            "transcript": result["transcript"],
            "frame_count": len(frame_paths),
            "vision_observations": result["vision_observations"],
        }
        save_memory(
            f"Media analiz notu: {file.filename}\nKare sayisi: {len(result['frames'])}\n"
            f"Transkript: {result['transcript'][:12000]}\nRapor: {json.dumps(result['report'], ensure_ascii=False)[:20000]}"
        )
        return result
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise HTTPException(422, f"Media analizi basarisiz: {exc}") from exc


@app.post("/api/memory")
def add_memory(request: MemoryRequest) -> dict[str, str]:
    note = request.note.strip()
    if not note:
        raise HTTPException(400, "Not bos olamaz.")
    save_typed_memory(note, request.category, request.project, request.source)
    return {"status": "saved", "category": request.category, "project": request.project, "source": request.source}


@app.post("/api/upload")
async def upload(file: UploadFile = File(...)) -> dict[str, str]:
    data = read_upload(file)
    name = file.filename or "upload"
    suffix = Path(name).suffix.lower()
    if suffix in {".pdf", ".docx", ".pptx", ".xlsx", ".xlsm", ".txt", ".md", ".py", ".json", ".ts", ".tsx"}:
        text = extract_document_text(data, suffix)
    elif suffix in {".png", ".jpg", ".jpeg", ".webp"}:
        structure = document_structure(data, suffix)
        ocr = optional_ocr(data, suffix)
        text = structure + "\nVision analizi:\n" + call_ollama_vision(
            data,
            "Bu gorseli ayrintili ama kanita dayali analiz et. Gorunen metni, nesneleri, duzeni ve belirsizlikleri belirt.",
            suffix,
        )
        text += f"\nOCR ({'hazir' if ocr['available'] else 'kullanilamadi'}):\n{ocr['text'] or ocr['reason']}"
    else:
        text = f"{name} yuklendi; bu dosya turu icin ozel extractor henuz etkin degil."
    note = f"Dosya: {name}\nYapi: {document_structure(data, suffix)}\n{text[:12000]}"
    with db() as connection:
        connection.execute("INSERT INTO memories(note) VALUES (?)", (note,))
    return {"status": "indexed", "filename": name, "preview": text[:1000]}


@app.post("/api/report/export")
def export_report(request: ReportExportRequest) -> FileResponse:
    if request.format not in {"md", "pdf"}:
        raise HTTPException(400, "Format md veya pdf olmali.")
    markdown = report_markdown(request.title, request.report, request.sources)
    output = Path(tempfile.gettempdir()) / f"localqwen_report_{uuid.uuid4().hex}.{request.format}"
    if request.format == "md":
        output.write_text(markdown, encoding="utf-8")
        return FileResponse(output, media_type="text/markdown", filename="localqwen_report.md")
    pdf_canvas = canvas.Canvas(str(output), pagesize=A4)
    pdf_canvas.setTitle(request.title)
    text_object = pdf_canvas.beginText(48, 800)
    text_object.setFont("Helvetica", 9)
    for line in markdown.encode("ascii", "replace").decode("ascii").splitlines():
        text_object.textLine(line[:115])
        if text_object.getY() < 48:
            pdf_canvas.drawText(text_object)
            pdf_canvas.showPage()
            text_object = pdf_canvas.beginText(48, 800)
            text_object.setFont("Helvetica", 9)
    pdf_canvas.drawText(text_object)
    pdf_canvas.save()
    return FileResponse(output, media_type="application/pdf", filename="localqwen_report.pdf")


@app.post("/api/pdf/append")
async def append_pdf(file: UploadFile = File(...), addition: str = Form(...)) -> FileResponse:
    """Append user-provided text as a new PDF page and return the result."""
    data = read_upload(file)
    if Path(file.filename or "").suffix.lower() != ".pdf":
        raise HTTPException(400, "Bu islem icin PDF dosyasi yukleyin.")
    addition = addition.strip()
    if not addition:
        raise HTTPException(400, "Eklenecek metin bos olamaz.")

    try:
        original = PdfReader(io.BytesIO(data))
        page_buffer = io.BytesIO()
        page_canvas = canvas.Canvas(page_buffer, pagesize=A4)
        width, height = A4
        page_canvas.setFont("Helvetica-Bold", 14)
        page_canvas.drawString(54, height - 60, "Ek Bilgi")
        page_canvas.setFont("Helvetica", 10)
        y = height - 90
        for paragraph in addition.splitlines() or [addition]:
            words = paragraph.split()
            line = ""
            for word in words:
                candidate = f"{line} {word}".strip()
                if page_canvas.stringWidth(candidate, "Helvetica", 10) > width - 108:
                    page_canvas.drawString(54, y, line)
                    y -= 16
                    line = word
                else:
                    line = candidate
            page_canvas.drawString(54, y, line)
            y -= 16
            if y < 54:
                page_canvas.showPage()
                page_canvas.setFont("Helvetica", 10)
                y = height - 54
        page_canvas.save()
        page_buffer.seek(0)

        writer = PdfWriter()
        for page in original.pages:
            writer.add_page(page)
        writer.add_page(PdfReader(page_buffer).pages[0])
        output = Path(tempfile.gettempdir()) / f"localqwen_{next(tempfile._get_candidate_names())}.pdf"
        with output.open("wb") as stream:
            writer.write(stream)
    except Exception as exc:
        raise HTTPException(422, f"PDF olusturulamadi: {exc}") from exc

    return FileResponse(output, media_type="application/pdf", filename="localqwen_modified.pdf")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8787)
