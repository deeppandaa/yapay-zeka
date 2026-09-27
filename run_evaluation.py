from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

from agent_orchestrator import decide, plan_for

ROOT = Path(__file__).resolve().parent
CASES = ROOT / "evaluation_cases.json"
ARTIFACTS = ROOT / ".job-artifacts"


def source_hashes() -> dict[str, str]:
    hashes = {}
    for path in (ROOT / "agent_orchestrator.py", ROOT / "agent_tools.py", CASES):
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        hashes[path.name] = digest
    return hashes


def run() -> int:
    started = time.perf_counter()
    cases = json.loads(CASES.read_text(encoding="utf-8"))
    failures: list[str] = []
    for case in cases:
        decision = decide(case["message"])
        plan = " ".join(plan_for(case["message"])).lower()
        case_failed = False
        if decision.intent != case["expected_intent"]:
            failures.append(f"{case['name']}: intent={decision.intent!r}")
            case_failed = True
        for term in case["required_plan_terms"]:
            if term.lower() not in plan:
                failures.append(f"{case['name']}: plan missing {term!r}")
                case_failed = True
        print(f"{'FAIL' if case_failed else 'PASS'} {case['name']} intent={decision.intent}")
    print(f"TOTAL={len(cases)} FAILURES={len(failures)}")
    ARTIFACTS.mkdir(exist_ok=True)
    artifact = {
        "suite": "offline-coding-agent-hard",
        "case_count": len(cases),
        "failure_count": len(failures),
        "passed": not failures,
        "duration_seconds": round(time.perf_counter() - started, 3),
        "source_hashes": source_hashes(),
        "failures": failures,
    }
    artifact_path = ARTIFACTS / f"evaluation-{int(time.time())}.json"
    artifact_path.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"ARTIFACT={artifact_path}")
    if failures:
        print("\n".join(failures))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(run())
