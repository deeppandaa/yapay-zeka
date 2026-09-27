from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT.parent / "DeepPanda-Gemma4-submission.zip"
REQUIRED = [
    ROOT / "agent.yaml",
    ROOT / "eval_config.yaml",
    ROOT / "prompts" / "system.md",
    ROOT / "sub_agents" / "code_analyzer.yaml",
    ROOT / "sub_agents" / "test_reviewer.yaml",
    ROOT / "skills" / "repo_navigation" / "SKILL.md",
]
PACKAGE_ROOTS = [ROOT / "agent.yaml", ROOT / "eval_config.yaml", ROOT / "prompts", ROOT / "sub_agents", ROOT / "skills"]

missing = [str(path.relative_to(ROOT)) for path in REQUIRED if not path.is_file()]
if missing:
    raise SystemExit(f"Missing submission files: {missing}")

with ZipFile(OUTPUT, "w", ZIP_DEFLATED) as archive:
    for package_root in PACKAGE_ROOTS:
        paths = [package_root] if package_root.is_file() else package_root.rglob("*")
        for path in paths:
            if path.is_file():
                archive.write(path, path.relative_to(ROOT).as_posix())

with ZipFile(OUTPUT) as archive:
    names = set(archive.namelist())
    if "agent.yaml" not in names:
        raise SystemExit("agent.yaml is not at the archive root")

print(OUTPUT)
