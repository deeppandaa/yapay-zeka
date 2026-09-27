@echo off
wsl.exe -d Ubuntu -- bash -lc "export ADAPTER_PATH='/mnt/d/DeepPanda-Proje/Yapay Zeka/AI-Runtimes/models/localqwen-offline-lora-v3'; export PORT=11435; '/mnt/d/DeepPanda-Proje/Yapay Zeka/.venv-wsl/bin/python' '/mnt/d/DeepPanda-Proje/Yapay Zeka/training/adapter_server.py'"
pause
