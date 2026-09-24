from __future__ import annotations

import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LIBRARIES = ROOT / "AI-Libraries"
DB = ROOT / "memory.db"
CATALOG = ROOT / "library_catalog.json"
ALLOWED = {"README.md", "README.rst", "pyproject.toml", "setup.py", "requirements.txt"}


def main() -> None:
    catalog = {item["name"]: item for item in json.loads(CATALOG.read_text(encoding="utf-8"))}
    with sqlite3.connect(DB) as connection:
        connection.execute(
            "CREATE TABLE IF NOT EXISTS memories (id INTEGER PRIMARY KEY, note TEXT NOT NULL, category TEXT NOT NULL DEFAULT 'general', project TEXT NOT NULL DEFAULT '', source TEXT NOT NULL DEFAULT 'user', created_at TEXT DEFAULT CURRENT_TIMESTAMP)"
        )
        connection.execute("DELETE FROM memories WHERE category = 'library_knowledge' AND source LIKE 'git:%'")
        for name, item in catalog.items():
            repo = LIBRARIES / name
            if not repo.is_dir():
                continue
            for path in repo.rglob("*"):
                if not path.is_file() or path.name not in ALLOWED or ".git" in path.parts:
                    continue
                text = path.read_text(encoding="utf-8", errors="replace")[:12000].strip()
                if not text:
                    continue
                note = f"Yerel kutuphane bilgisi: {name}\nDosya: {path.relative_to(repo)}\nKategori: {item['category']}\nKaynak: {item['repo']}\n\n{text}"
                duplicate = connection.execute(
                    "SELECT 1 FROM memories WHERE note = ? AND category = ? AND project = ? AND source = ? LIMIT 1",
                    (note, "library_knowledge", "DeepPanda", "git:" + item["repo"]),
                ).fetchone()
                if not duplicate:
                    connection.execute(
                        "INSERT INTO memories(note, category, project, source) VALUES (?, ?, ?, ?)",
                        (note, "library_knowledge", "DeepPanda", "git:" + item["repo"]),
                    )
    print("Library docs indexed into memory.db")


if __name__ == "__main__":
    main()
