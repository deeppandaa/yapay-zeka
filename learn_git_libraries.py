from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LIBRARIES = ROOT / "AI-Libraries"
DB = ROOT / "memory.db"
CATALOG = ROOT / "library_catalog.json"
ALLOWED = {"README.md", "README.rst", "pyproject.toml", "setup.py", "requirements.txt"}


def main() -> None:
    parser = argparse.ArgumentParser(description="Index local library documentation into persistent memory.")
    parser.add_argument("--name", action="append", help="Index only this catalog entry; may be repeated.")
    args = parser.parse_args()
    catalog = {item["name"]: item for item in json.loads(CATALOG.read_text(encoding="utf-8"))}
    if args.name:
        missing = set(args.name) - set(catalog)
        if missing:
            parser.error("Unknown library name(s): " + ", ".join(sorted(missing)))
        catalog = {name: catalog[name] for name in args.name}
    with sqlite3.connect(DB) as connection:
        connection.execute(
            "CREATE TABLE IF NOT EXISTS memories (id INTEGER PRIMARY KEY, note TEXT NOT NULL, category TEXT NOT NULL DEFAULT 'general', project TEXT NOT NULL DEFAULT '', source TEXT NOT NULL DEFAULT 'user', created_at TEXT DEFAULT CURRENT_TIMESTAMP)"
        )
        if not args.name:
            connection.execute("DELETE FROM memories WHERE category = 'library_knowledge' AND source LIKE 'git:%'")
        for name, item in catalog.items():
            source_path = LIBRARIES / item.get("path", name)
            if source_path.is_file():
                paths = [source_path]
                root = source_path.parent
            elif source_path.is_dir():
                paths = source_path.rglob("*")
                root = source_path
            else:
                continue
            source = item.get("source", "git:" + item["repo"])
            for path in paths:
                explicitly_catalogued_markdown = source_path.is_file() and path == source_path and path.suffix.lower() == ".md"
                if not path.is_file() or (path.name not in ALLOWED and not explicitly_catalogued_markdown) or ".git" in path.parts:
                    continue
                text = path.read_text(encoding="utf-8", errors="replace")[:12000].strip()
                if not text:
                    continue
                note = f"Yerel kutuphane bilgisi: {name}\nDosya: {path.relative_to(root)}\nKategori: {item['category']}\nKaynak: {item['repo']}\n\n{text}"
                duplicate = connection.execute(
                    "SELECT 1 FROM memories WHERE note = ? AND category = ? AND project = ? AND source = ? LIMIT 1",
                    (note, "library_knowledge", "DeepPanda", source),
                ).fetchone()
                if not duplicate:
                    connection.execute(
                        "INSERT INTO memories(note, category, project, source) VALUES (?, ?, ?, ?)",
                        (note, "library_knowledge", "DeepPanda", source),
                    )
    print("Library docs indexed into memory.db")


if __name__ == "__main__":
    main()
