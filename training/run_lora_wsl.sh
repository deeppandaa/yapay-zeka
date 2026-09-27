#!/usr/bin/env bash
set -euo pipefail
ROOT="/mnt/d/DeepPanda-Proje/Yapay Zeka"
PYTHON="$ROOT/.venv-wsl/bin/python"
exec "$PYTHON" "$ROOT/training/train_lora.py" "$@"
