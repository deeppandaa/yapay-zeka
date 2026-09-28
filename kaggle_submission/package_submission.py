from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from validate_submission import main as validate_submission

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT.parent / "DeepPanda-Gemma4-submission.zip"
MAX_TOTAL_BYTES = 3 * 1024**3
ALLOWED_SUFFIXES = {".yaml", ".yml", ".md", ".txt", ".py", ".json", ".safetensors"}
REQUIRED = [
    ROOT / "agent.yaml",
    ROOT / "eval_config.yaml",
    ROOT / "prompts" / "system.md",
    ROOT / "sub_agents" / "code_analyzer.yaml",
    ROOT / "sub_agents" / "test_reviewer.yaml",
    ROOT / "skills" / "repo_navigation" / "SKILL.md",
]
PACKAGE_ROOTS = [ROOT / "agent.yaml", ROOT / "eval_config.yaml", ROOT / "configs", ROOT / "prompts", ROOT / "sub_agents", ROOT / "skills"]

missing = [str(path.relative_to(ROOT)) for path in REQUIRED if not path.is_file()]
if missing:
    raise SystemExit(f"Missing submission files: {missing}")
try:
    validate_submission()
except SystemExit as exc:
    raise SystemExit(exc.code) from exc

package_files = []
total_bytes = 0
for package_root in PACKAGE_ROOTS:
    paths = [package_root] if package_root.is_file() else package_root.rglob("*")
    for path in paths:
        if path.is_symlink():
            raise SystemExit(f"Symlinks are not allowed: {path.relative_to(ROOT)}")
        if not path.is_file() or "__pycache__" in path.parts or path.suffix == ".pyc":
            continue
        if path.suffix.lower() not in ALLOWED_SUFFIXES:
            raise SystemExit(f"Unsupported file type: {path.relative_to(ROOT)}")
        total_bytes += path.stat().st_size
        if total_bytes >= MAX_TOTAL_BYTES:
            raise SystemExit("Unpacked submission exceeds the 3 GiB competition limit")
        package_files.append(path)

with ZipFile(OUTPUT, "w", ZIP_DEFLATED) as archive:
    for path in sorted(package_files):
        archive.write(path, path.relative_to(ROOT).as_posix())

with ZipFile(OUTPUT) as archive:
    names = set(archive.namelist())
    if "agent.yaml" not in names:
        raise SystemExit("agent.yaml is not at the archive root")

print(OUTPUT)
