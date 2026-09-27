from __future__ import annotations

import argparse
import json
from pathlib import Path

from datasets import Dataset
from peft import LoraConfig, TaskType, get_peft_model
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    DataCollatorForLanguageModeling,
    Trainer,
    TrainingArguments,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET = ROOT / "training" / "offline_agent_tasks.jsonl"
DEFAULT_OUTPUT = ROOT / "AI-Runtimes" / "models" / "localqwen-offline-lora"
DEFAULT_MODEL = "Qwen/Qwen2.5-0.5B-Instruct"


def load_records(path: Path) -> list[dict[str, object]]:
    records = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            records.append(json.loads(line))
    if not records:
        raise ValueError("Egitim seti bos.")
    return records


def build_dataset(tokenizer, records: list[dict[str, object]], max_length: int) -> Dataset:
    def encode(example: dict[str, object]) -> dict[str, list[int]]:
        messages = example["messages"]
        prompt_messages = messages[:-1]
        prompt_text = tokenizer.apply_chat_template(prompt_messages, tokenize=False, add_generation_prompt=True)
        full_text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=False)
        prompt_tokens = tokenizer(prompt_text, truncation=True, max_length=max_length)["input_ids"]
        full_tokens = tokenizer(full_text, truncation=True, max_length=max_length)["input_ids"]
        prompt_length = min(len(prompt_tokens), len(full_tokens))
        return {
            "input_ids": full_tokens,
            "attention_mask": [1] * len(full_tokens),
            "labels": [-100] * prompt_length + full_tokens[prompt_length:],
        }

    return Dataset.from_list(records).map(encode, remove_columns=["id", "tags", "messages"])


def main() -> None:
    parser = argparse.ArgumentParser(description="Train a small local Qwen LoRA adapter from offline agent examples.")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--epochs", type=float, default=3.0)
    parser.add_argument("--max-length", type=int, default=1024)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    records = load_records(args.dataset)
    if args.dry_run:
        print(json.dumps({"records": len(records), "model": args.model, "output": str(args.output), "max_length": args.max_length}, ensure_ascii=False))
        return

    tokenizer = AutoTokenizer.from_pretrained(args.model, use_fast=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(args.model, torch_dtype="auto", device_map="auto")
    config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=16,
        lora_alpha=32,
        lora_dropout=0.05,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    )
    model = get_peft_model(model, config)
    model.print_trainable_parameters()
    dataset = build_dataset(tokenizer, records, args.max_length)
    args.output.mkdir(parents=True, exist_ok=True)
    training = TrainingArguments(
        output_dir=str(args.output),
        num_train_epochs=args.epochs,
        per_device_train_batch_size=1,
        gradient_accumulation_steps=8,
        learning_rate=2e-4,
        logging_steps=1,
        save_strategy="epoch",
        report_to="none",
        remove_unused_columns=False,
        fp16=False,
        bf16=False,
    )
    trainer = Trainer(
        model=model,
        args=training,
        train_dataset=dataset,
        data_collator=DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False),
    )
    trainer.train()
    model.save_pretrained(args.output)
    tokenizer.save_pretrained(args.output)
    print(f"LoRA adapter kaydedildi: {args.output}")


if __name__ == "__main__":
    main()
