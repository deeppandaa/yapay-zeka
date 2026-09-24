from __future__ import annotations

import shutil
import subprocess
import sys
import time
import uuid
from difflib import unified_diff
from pathlib import Path


class AgentTools:
    """Constrained tools: workspace-only writes and explicit command approval."""

    def __init__(self, workspace: Path):
        self.workspace = workspace.resolve()
        self.backup_root = self.workspace / ".localqwen-backups"

    def safe_path(self, relative: str) -> Path:
        path = (self.workspace / relative).resolve()
        if path != self.workspace and self.workspace not in path.parents:
            raise ValueError("Workspace disi dosya erisimi engellendi.")
        return path

    def write_file(self, relative: str, content: str) -> dict[str, object]:
        target = self.safe_path(relative)
        target.parent.mkdir(parents=True, exist_ok=True)
        backup_path = ""
        if target.exists():
            backup = self.backup_root / uuid.uuid4().hex / relative
            backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(target, backup)
            backup_path = str(backup)
        target.write_text(content, encoding="utf-8")
        return {"path": str(target), "backup": backup_path, "created": not bool(backup_path)}

    def rollback_write(self, result: dict[str, object]) -> dict[str, str]:
        target = self.safe_path(str(result["path"]))
        backup = str(result.get("backup", ""))
        if backup:
            backup_path = Path(backup).resolve()
            if self.backup_root not in backup_path.parents:
                raise ValueError("Gecersiz backup yolu.")
            if not backup_path.is_file():
                raise ValueError("Backup dosyasi bulunamadi.")
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(backup_path, target)
            return {"path": str(target), "action": "restored"}
        if target.exists():
            target.unlink()
        return {"path": str(target), "action": "removed_created_file"}

    def preview_write(self, relative: str, content: str) -> dict[str, str]:
        target = self.safe_path(relative)
        before = target.read_text(encoding="utf-8", errors="replace") if target.exists() else ""
        diff = "".join(
            unified_diff(
                before.splitlines(keepends=True),
                content.splitlines(keepends=True),
                fromfile=str(target),
                tofile=str(target),
            )
        )
        return {"path": str(target), "diff": diff, "status": "new" if not target.exists() else "modified"}

    def read_file(self, relative: str, max_bytes: int = 2_000_000) -> dict[str, str]:
        target = self.safe_path(relative)
        if not target.is_file():
            raise ValueError("Dosya bulunamadi.")
        if target.stat().st_size > max_bytes:
            raise ValueError("Dosya boyutu okuma sinirini asiyor.")
        return {"path": str(target), "content": target.read_text(encoding="utf-8", errors="replace")}

    def run_approved(self, command: list[str], approved: bool = False) -> dict[str, object]:
        if not approved:
            return {"status": "approval_required", "command": command}
        allowed_names = {"python", "py", "node", "npm", "pytest", "ruff", "ffmpeg", "ollama", "winget"}
        executable = Path(command[0]).resolve() if command else None
        if not command or (command[0].lower() not in allowed_names and executable != Path(sys.executable).resolve()):
            raise ValueError("Yalnizca izinli araclar calistirilabilir.")
        started = time.perf_counter()
        result = subprocess.run(
            command,
            cwd=self.workspace,
            capture_output=True,
            text=True,
            timeout=300,
            shell=False,
            check=False,
        )
        duration = round(time.perf_counter() - started, 3)
        passed = result.returncode == 0
        return {
            "status": "completed",
            "passed": passed,
            "returncode": result.returncode,
            "duration_seconds": duration,
            "command": command,
            "report": "Basarili" if passed else "Basarisiz",
            "stdout": result.stdout[-12000:],
            "stderr": result.stderr[-12000:],
        }
