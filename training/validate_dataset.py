from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET = ROOT / "training" / "offline_agent_tasks.jsonl"
REQUIRED_ROLES = {"system", "user", "assistant"}

parser = argparse.ArgumentParser()
parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
args = parser.parse_args()
records = [json.loads(line) for line in args.dataset.read_text(encoding="utf-8").splitlines() if line.strip()]
ids = [record.get("id") for record in records]
errors: list[str] = []
for record in records:
    messages = record.get("messages", [])
    roles = {message.get("role") for message in messages if isinstance(message, dict)}
    if not REQUIRED_ROLES.issubset(roles):
        errors.append(f"{record.get('id')}: missing message role")
    if len(messages) < 3:
        errors.append(f"{record.get('id')}: too few messages")
    if not record.get("tags"):
        errors.append(f"{record.get('id')}: no tags")
if len(ids) != len(set(ids)):
    errors.append("duplicate ids")
if errors:
    raise SystemExit("\n".join(errors))
print({"records": len(records), "unique_ids": len(set(ids)), "tags": Counter(tag for record in records for tag in record["tags"])})
