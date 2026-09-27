from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer

ROOT = Path(__file__).resolve().parents[1]
CASES = ROOT / "training" / "quality_eval_cases.jsonl"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--adapter", required=True)
    parser.add_argument("--model", default="Qwen/Qwen2.5-0.5B-Instruct")
    parser.add_argument("--output", type=Path, default=ROOT / "training" / "results")
    args = parser.parse_args()
    cases = [json.loads(line) for line in CASES.read_text(encoding="utf-8").splitlines() if line.strip()]
    tokenizer = AutoTokenizer.from_pretrained(args.model)
    model = AutoModelForCausalLM.from_pretrained(args.model, torch_dtype="auto").to("cuda" if torch.cuda.is_available() else "cpu")
    model = PeftModel.from_pretrained(model, args.adapter).eval()
    device = next(model.parameters()).device
    results = []
    for case in cases:
        text = tokenizer.apply_chat_template([{"role": "user", "content": case["prompt"]}], tokenize=False, add_generation_prompt=True)
        inputs = tokenizer(text, return_tensors="pt").to(device)
        started = time.perf_counter()
        with torch.no_grad():
            output = model.generate(**inputs, max_new_tokens=180, do_sample=False)
        answer = tokenizer.decode(output[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
        lowered = answer.lower()
        required = [term for term in case["required"] if term.lower() in lowered]
        forbidden = [term for term in case["forbidden"] if term.lower() in lowered]
        results.append({"id": case["id"], "category": case["category"], "score": len(required) / max(1, len(case["required"])), "required_found": required, "forbidden_found": forbidden, "answer": answer, "seconds": round(time.perf_counter() - started, 3)})
    summary = {"adapter": args.adapter, "case_count": len(results), "average_score": sum(item["score"] for item in results) / len(results), "forbidden_cases": sum(bool(item["forbidden_found"]) for item in results), "results": results}
    args.output.mkdir(parents=True, exist_ok=True)
    output_path = args.output / f"adapter-evaluation-{Path(args.adapter).name}.json"
    output_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"average_score": summary["average_score"], "forbidden_cases": summary["forbidden_cases"], "output": str(output_path)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
