from pathlib import Path

from agent_orchestrator import decide, plan_for
from agent_tools import AgentTools


def test_core_modules_and_plan_are_importable():
    import app

    assert app.app.title == "LocalQwenAgent"
    assert (Path(__file__).parent / "AI_MASTER_PLAN.md").is_file()


def test_intent_and_plan_for_action_request(tmp_path: Path):
    decision = decide("projeyi test et ve installer olustur")
    assert decision.intent == "action_request"
    assert decision.needs_tool_approval is True
    assert plan_for("projeyi test et")


def test_workspace_write_is_scoped_and_backed_up(tmp_path: Path):
    tools = AgentTools(tmp_path)
    tools.write_file("notes.txt", "first")
    result = tools.write_file("notes.txt", "second")
    assert (tmp_path / "notes.txt").read_text() == "second"
    assert list((tmp_path / ".localqwen-backups").rglob("notes.txt"))
    assert result["backup"]


def test_workspace_traversal_is_rejected(tmp_path: Path):
    tools = AgentTools(tmp_path)
    try:
        tools.safe_path("../outside.txt")
    except ValueError:
        return
    raise AssertionError("workspace traversal was not rejected")


def test_workspace_write_preview_does_not_modify_file(tmp_path: Path):
    tools = AgentTools(tmp_path)
    tools.write_file("notes.txt", "first\n")
    preview = tools.preview_write("notes.txt", "second\n")
    assert preview["status"] == "modified"
    assert "-first" in preview["diff"]
    assert "+second" in preview["diff"]
    assert (tmp_path / "notes.txt").read_text() == "first\n"


def test_workspace_rollback_restores_previous_file(tmp_path: Path):
    tools = AgentTools(tmp_path)
    tools.write_file("notes.txt", "first\n")
    result = tools.write_file("notes.txt", "second\n")
    tools.rollback_write(result)
    assert (tmp_path / "notes.txt").read_text() == "first\n"


def test_workspace_rollback_removes_new_file(tmp_path: Path):
    tools = AgentTools(tmp_path)
    result = tools.write_file("new.txt", "created\n")
    tools.rollback_write(result)
    assert not (tmp_path / "new.txt").exists()