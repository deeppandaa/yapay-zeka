@echo off
wsl.exe -d Ubuntu -- bash -lc "'/mnt/d/DeepPanda-Proje/Yapay Zeka/.venv-wsl/bin/python' '/mnt/d/DeepPanda-Proje/Yapay Zeka/training/split_dataset.py' && '/mnt/d/DeepPanda-Proje/Yapay Zeka/.venv-wsl/bin/python' '/mnt/d/DeepPanda-Proje/Yapay Zeka/training/train_lora.py' --dataset '/mnt/d/DeepPanda-Proje/Yapay Zeka/training/splits/train.jsonl' --output '/mnt/d/DeepPanda-Proje/Yapay Zeka/AI-Runtimes/models/localqwen-offline-lora-v3'"
pause
