from __future__ import annotations

import os
from typing import Any

import torch
import uvicorn
from fastapi import FastAPI
from peft import PeftModel
from pydantic import BaseModel
from transformers import AutoModelForCausalLM, AutoTokenizer

BASE_MODEL = os.getenv("BASE_MODEL", "Qwen/Qwen2.5-0.5B-Instruct")
ADAPTER_PATH = os.getenv("ADAPTER_PATH", "/mnt/d/DeepPanda-Proje/Yapay Zeka/AI-Runtimes/models/localqwen-offline-lora-v3")
PORT = int(os.getenv("PORT", "11435"))
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

app = FastAPI(title="LocalQwen LoRA Adapter")
tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)
base_model = AutoModelForCausalLM.from_pretrained(BASE_MODEL, torch_dtype="auto").to(DEVICE)
model = PeftModel.from_pretrained(base_model, ADAPTER_PATH).eval()


class ChatRequest(BaseModel):
    model: str = "localqwen-lora-v3"
    messages: list[dict[str, Any]]
    stream: bool = False
    options: dict[str, Any] = {}


@app.get("/api/tags")
def tags() -> dict[str, list[dict[str, Any]]]:
    return {"models": [{"name": "localqwen-lora-v3", "base_model": BASE_MODEL, "adapter": ADAPTER_PATH, "device": DEVICE}]}


@app.post("/api/chat")
def chat(request: ChatRequest) -> dict[str, Any]:
    text = tokenizer.apply_chat_template(request.messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer(text, return_tensors="pt").to(DEVICE)
    max_tokens = int(request.options.get("num_predict", 256))
    with torch.no_grad():
        output = model.generate(**inputs, max_new_tokens=max_tokens, do_sample=False)
    answer = tokenizer.decode(output[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
    return {"model": request.model, "message": {"role": "assistant", "content": answer}, "done": True}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT)
