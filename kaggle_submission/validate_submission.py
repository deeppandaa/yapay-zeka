from __future__ import annotations

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent
SUPPORTED_MODEL = "gemma-4-31b-it-qat-w4a16-ct"
MAX_SUBMISSION_BYTES = 3 * 1024**3
ALLOWED_SUFFIXES = {".yaml", ".yml", ".md", ".txt", ".py", ".json", ".safetensors"}
PACKAGE_ROOTS = ("agent.yaml", "eval_config.yaml", "configs", "prompts", "sub_agents", "skills")


class IncludeLoader(yaml.SafeLoader):
    pass


IncludeLoader.add_constructor("!include", lambda loader, node: loader.construct_scalar(node))


def fail(message: str) -> None:
    raise SystemExit(message)


def inside_root(path: Path) -> bool:
    try:
        path.resolve().relative_to(ROOT.resolve())
        return True
    except ValueError:
        return False


def load_yaml(relative: str) -> dict:
    path = (ROOT / relative).resolve()
    if not inside_root(path) or not path.is_file():
        fail(f"missing or unsafe YAML: {relative}")
    try:
        data = yaml.load(path.read_text(encoding="utf-8"), Loader=IncludeLoader)
    except (OSError, yaml.YAMLError) as exc:
        fail(f"invalid YAML {relative}: {exc}")
    if not isinstance(data, dict):
        fail(f"YAML root must be a mapping: {relative}")
    return data


def check_include(config_path: str, include_path: str) -> None:
    if not include_path or "\x00" in include_path:
        fail(f"invalid !include in {config_path}")
    target = (ROOT / config_path).parent.joinpath(include_path).resolve()
    if not inside_root(target) or not target.is_file():
        fail(f"!include missing or escapes submission root: {config_path} -> {include_path}")


def check_agent(relative: str, root_agent: bool = False) -> dict:
    config = load_yaml(relative)
    if config.get("model") != SUPPORTED_MODEL:
        fail(f"{relative} must use the supported Gemma 4 model")
    if not config.get("name") or not isinstance(config.get("instruction"), str):
        fail(f"{relative} needs name and instruction")
    check_include(relative, config["instruction"])
    generation = config.get("generate_content_config")
    if generation is not None:
        if not isinstance(generation, str):
            fail(f"generate_content_config must be a relative !include in {relative}")
        check_include(relative, generation)
    tools = config.get("tools", [])
    if not isinstance(tools, list):
        fail(f"tools must be a list in {relative}")
    direct_tools: set[str] = set()
    for tool in tools:
        if isinstance(tool, str):
            direct_tools.add(tool)
            continue
        if not isinstance(tool, dict):
            fail(f"invalid tool declaration in {relative}: {tool!r}")
        if isinstance(tool.get("name"), str):
            direct_tools.add(tool["name"])
        agent_tool = tool.get("agent_tool")
        if agent_tool is not None:
            if not isinstance(agent_tool, dict) or not isinstance(agent_tool.get("config_path"), str):
                fail(f"invalid agent_tool declaration in {relative}")
            config_target = (ROOT / relative).parent.joinpath(agent_tool["config_path"]).resolve()
            if not inside_root(config_target) or not config_target.is_file():
                fail(f"agent_tool config missing or unsafe: {relative} -> {agent_tool['config_path']}")
            check_agent(config_target.relative_to(ROOT).as_posix())
    if root_agent:
        required_tools = {
            "read_file", "edit_file", "write_file", "run_command", "get_status", "submit_patch",
            "get_code_neighbors", "search_similar_code", "get_code_subgraph",
        }
        missing = sorted(required_tools - direct_tools)
        if missing:
            fail(f"agent.yaml missing required tools: {', '.join(missing)}")
        skills = config.get("skills", [])
        if not isinstance(skills, list) or not skills:
            fail("agent.yaml must register at least one skill")
        for skill in skills:
            skill_dir = (ROOT / skill).resolve()
            manifest = skill_dir / "SKILL.md"
            if not inside_root(manifest) or not manifest.is_file():
                fail(f"skill manifest missing or unsafe: {skill}")
            skill_text = manifest.read_text(encoding="utf-8")
            if not re.search(r"(?ms)^---\s*\n.*?^name:\s*\S+.*?^---\s*$", skill_text):
                fail(f"skill manifest needs YAML name frontmatter: {skill}")
    return config


def main() -> None:
    required_files = (
        "agent.yaml",
        "eval_config.yaml",
        "configs/sampling.yaml",
        "prompts/system.md",
        "prompts/code_analyzer.md",
        "prompts/test_reviewer.md",
        "sub_agents/code_analyzer.yaml",
        "sub_agents/test_reviewer.yaml",
        "skills/repo_navigation/SKILL.md",
    )
    total_bytes = 0
    for relative_root in PACKAGE_ROOTS:
        package_root = ROOT / relative_root
        paths = [package_root] if package_root.is_file() else package_root.rglob("*")
        for path in paths:
            if path.is_symlink():
                fail(f"symlinks are not allowed in submission: {path.relative_to(ROOT)}")
            if not path.is_file() or "__pycache__" in path.parts or path.suffix == ".pyc":
                continue
            if path.suffix.lower() not in ALLOWED_SUFFIXES:
                fail(f"unsupported submission file type: {path.relative_to(ROOT)}")
            total_bytes += path.stat().st_size
    if total_bytes >= MAX_SUBMISSION_BYTES:
        fail(f"unpacked submission exceeds 3 GiB: {total_bytes} bytes")
    for relative in required_files:
        path = ROOT / relative
        if not path.is_file():
            fail(f"missing: {relative}")

    root_config = check_agent("agent.yaml", root_agent=True)
    for relative in ("sub_agents/code_analyzer.yaml", "sub_agents/test_reviewer.yaml"):
        check_agent(relative)

    eval_config = load_yaml("eval_config.yaml").get("evaluation")
    if not isinstance(eval_config, dict):
        fail("eval_config.yaml must contain an evaluation mapping")
    for key in ("timeout_seconds", "max_tool_calls", "max_time_minutes", "max_turns"):
        if not isinstance(eval_config.get(key), (int, float)) or eval_config[key] <= 0:
            fail(f"eval_config.yaml evaluation.{key} must be a positive number")

    print(f"submission files: ok; agent={root_config['name']}; bytes={total_bytes}; evaluation={eval_config}")


if __name__ == "__main__":
    main()
