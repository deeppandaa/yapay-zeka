from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent


class IncludeLoader(yaml.SafeLoader):
    pass


IncludeLoader.add_constructor("!include", lambda loader, node: loader.construct_scalar(node))


required = [
    "agent.yaml",
    "eval_config.yaml",
    "prompts/system.md",
    "sub_agents/code_analyzer.yaml",
    "sub_agents/test_reviewer.yaml",
    "skills/repo_navigation/SKILL.md",
]
for relative in required:
    path = ROOT / relative
    if not path.is_file():
        raise SystemExit(f"missing: {relative}")

with (ROOT / "agent.yaml").open(encoding="utf-8") as handle:
    config = yaml.load(handle, Loader=IncludeLoader)
if config.get("model") != "gemma-4-31b-it-qat-w4a16-ct":
    raise SystemExit("agent.yaml must use the supported Gemma 4 model")
if not config.get("name") or not config.get("instruction"):
    raise SystemExit("agent.yaml needs name and instruction")
tools = {item.get("name") for item in config.get("tools", []) if isinstance(item, dict)}
for required_tool in ("read_file", "edit_file", "write_file", "run_command", "submit_patch"):
    if required_tool not in tools:
        raise SystemExit(f"agent.yaml missing required tool: {required_tool}")

print("submission files: ok")
