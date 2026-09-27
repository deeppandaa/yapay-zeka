from __future__ import annotations

import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATASET = Path(__file__).with_name("offline_agent_tasks.jsonl")
DB = ROOT / "memory.db"
REQUIRED_ROLES = {"system", "user", "assistant"}


def load_examples() -> list[dict[str, object]]:
    examples = []
    for line_number, line in enumerate(DATASET.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        item = json.loads(line)
        messages = item.get("messages")
        if not isinstance(item.get("id"), str) or not isinstance(messages, list):
            raise TypeError(f"Gecersiz egitim kaydi: satir {line_number}")
        roles = {message.get("role") for message in messages if isinstance(message, dict)}
        if not REQUIRED_ROLES.issubset(roles):
            raise ValueError(f"Rol eksik: satir {line_number}")
        examples.append(item)
    if not examples:
        raise ValueError("Egitim seti bos.")
    return examples


def index_memory(examples: list[dict[str, object]]) -> int:
    inserted = 0
    with sqlite3.connect(DB) as connection:
        connection.execute(
            "CREATE TABLE IF NOT EXISTS memories (id INTEGER PRIMARY KEY, note TEXT NOT NULL, category TEXT NOT NULL DEFAULT 'general', project TEXT NOT NULL DEFAULT '', source TEXT NOT NULL DEFAULT 'user', created_at TEXT DEFAULT CURRENT_TIMESTAMP)"
        )
        for item in examples:
            note = "Offline agent egitim ornegi\n" + json.dumps(item, ensure_ascii=False, indent=2)
            source = "offline-training:" + str(item["id"])
            exists = connection.execute(
                "SELECT 1 FROM memories WHERE source = ? AND project = ? LIMIT 1",
                (source, "DeepPanda"),
            ).fetchone()
            if not exists:
                connection.execute(
                    "INSERT INTO memories(note, category, project, source) VALUES (?, ?, ?, ?)",
                    (note[:40000], "procedure", "DeepPanda", source),
                )
                inserted += 1
    return inserted


if __name__ == "__main__":
    records = load_examples()
    inserted = index_memory(records)
    print(f"records={len(records)} indexed={inserted} dataset={DATASET}")
