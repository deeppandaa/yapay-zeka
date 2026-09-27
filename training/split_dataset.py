from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=ROOT / "training" / "offline_agent_tasks.jsonl")
    parser.add_argument("--output", type=Path, default=ROOT / "training" / "splits")
    parser.add_argument("--seed", type=int, default=20260927)
    args = parser.parse_args()

    records = [json.loads(line) for line in args.input.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len({record["id"] for record in records}) != len(records):
        raise ValueError("Duplicate dataset id")
    random.Random(args.seed).shuffle(records)
    train_end = max(1, int(len(records) * 0.8))
    validation_end = max(train_end + 1, int(len(records) * 0.9)) if len(records) > 2 else len(records)
    splits = {"train": records[:train_end], "validation": records[train_end:validation_end], "test": records[validation_end:]}
    args.output.mkdir(parents=True, exist_ok=True)
    for name, items in splits.items():
        (args.output / f"{name}.jsonl").write_text("\n".join(json.dumps(item, ensure_ascii=False) for item in items) + "\n", encoding="utf-8")
    print({name: len(items) for name, items in splits.items()})


if __name__ == "__main__":
    main()
