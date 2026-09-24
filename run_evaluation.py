from __future__ import annotations

import json
import sys
from pathlib import Path

from agent_orchestrator import decide, plan_for

ROOT = Path(__file__).resolve().parent
CASES = ROOT / "evaluation_cases.json"


def run() -> int:
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
    if failures:
        print("\n".join(failures))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(run())
