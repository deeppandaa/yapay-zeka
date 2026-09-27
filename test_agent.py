from pathlib import Path

from agent_orchestrator import decide, plan_for, system_prompt
from agent_tools import AgentTools


def test_core_modules_and_plan_are_importable():
    import app

    assert app.app.title == "LocalQwenAgent"
    assert (Path(__file__).parent / "AI_MASTER_PLAN.md").is_file()


def test_chat_and_embeddings_can_use_separate_ollama_endpoints(monkeypatch):
    import json

    import app

    requested_urls = []

    class Response:
        def __init__(self, payload):
            self.payload = payload

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def read(self):
            return json.dumps(self.payload).encode("utf-8")

    def fake_urlopen(request, timeout):
        requested_urls.append(request.full_url)
        if request.full_url.endswith("/api/embed"):
            return Response({"embeddings": [[0.1]]})
        return Response({"message": {"content": "ok"}})

    monkeypatch.setattr(app, "OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    monkeypatch.setattr(app, "OLLAMA_CHAT_BASE_URL", "http://127.0.0.1:11435")
    monkeypatch.setattr(app, "urlopen", fake_urlopen)

    assert app.call_ollama([{"role": "user", "content": "hello"}]) == "ok"
    assert app.ollama_embed(["hello"]) == [[0.1]]
    assert requested_urls == [
        "http://127.0.0.1:11435/api/chat",
        "http://127.0.0.1:11434/api/embed",
    ]


def test_general_chat_skips_workspace_scan(monkeypatch):
    import app

    def unexpected_workspace_scan(_query: str) -> str:
        raise AssertionError("General chat should not scan the workspace")

    monkeypatch.setattr(app, "workspace_context", unexpected_workspace_scan)
    monkeypatch.setattr(app, "call_ollama", lambda _messages: "Yozgat icin kisa bir onerim var.")

    response = app.chat(
        app.ChatRequest(
            message="Yozgat'a gidecegim, ne yapmami onerirsin?",
            memory=False,
        )
    )

    assert response["content"] == "Yozgat icin kisa bir onerim var."


def test_workspace_context_skips_virtualenv_and_cache_directories(tmp_path: Path, monkeypatch):
    import app

    (tmp_path / ".venv" / "Lib").mkdir(parents=True)
    (tmp_path / ".venv" / "Lib" / "matching.py").write_text("Yozgat venv noise", encoding="utf-8")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "matching.py").write_text("Yozgat source context", encoding="utf-8")
    monkeypatch.setattr(app, "WORKSPACE_ROOT", tmp_path)

    context = app.workspace_context("Yozgat")

    assert str(Path("src") / "matching.py") in context
    assert ".venv" not in context


def test_intent_and_plan_for_action_request(tmp_path: Path):
    decision = decide("projeyi test et ve installer olustur")
    assert decision.intent == "action_request"
    assert decision.needs_tool_approval is True
    assert plan_for("projeyi test et")


def test_system_prompt_protects_authenticated_sessions():
    decision = decide("private siteye giris yap")
    prompt = system_prompt(decision, "")
    assert "sifre" in prompt
    assert "cookie" in prompt
    assert "MFA" in prompt


def test_github_topic_parser_extracts_public_repositories():
    from app import GitHubTopicParser

    parser = GitHubTopicParser()
    parser.feed('<a href="/owner/repo">repo</a><a href="/topics/cnn">topic</a>')
    assert parser.repositories == {"https://github.com/owner/repo"}


def test_workspace_write_is_scoped_and_backed_up(tmp_path: Path):
    tools = AgentTools(tmp_path)
    tools.write_file("notes.txt", "first")
    result = tools.write_file("notes.txt", "second")
    assert (tmp_path / "notes.txt").read_text() == "second"
    assert list((tmp_path / ".localqwen-backups").rglob("notes.txt"))
    assert result["backup"]


def test_workspace_traversal_is_rejected(tmp_path: Path):
    tools = AgentTools(tmp_path)
    assert tools.safe_path("../outside.txt") != tmp_path / "outside.txt"


def test_protected_windows_path_is_rejected(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("WINDIR", r"C:\Windows")
    tools = AgentTools(tmp_path)
    try:
        tools.safe_path(r"C:\Windows\System32\drivers\etc\hosts")
    except ValueError:
        return
    raise AssertionError("protected Windows path was not rejected")


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


def test_chat_sessions_persist_list_history_and_delete(tmp_path: Path, monkeypatch):
    import app

    monkeypatch.setattr(app, "MEMORY_DB", tmp_path / "memory.db")
    session = app.create_chat_session(app.ChatSessionRequest(title="Uzun proje"))
    session_id = session["session_id"]
    monkeypatch.setattr(app, "workspace_context", lambda _query: "")
    monkeypatch.setattr(app, "call_ollama", lambda _messages: "Proje yaniti")

    response = app.chat(app.ChatRequest(message="Projeyi analiz et", session_id=session_id, memory=False))
    history = app.get_chat_messages(session_id)
    sessions = app.list_chat_sessions()["sessions"]

    assert response["session_id"] == session_id
    assert [message["role"] for message in history["messages"]] == ["user", "assistant"]
    assert sessions[0]["title"] == "Uzun proje"
    assert sessions[0]["message_count"] == 2

    assert app.delete_chat_session(session_id)["status"] == "deleted"
    assert app.list_chat_sessions()["sessions"] == []


def test_chat_session_history_is_added_to_followup_context(tmp_path: Path, monkeypatch):
    import app

    monkeypatch.setattr(app, "MEMORY_DB", tmp_path / "memory.db")
    monkeypatch.setattr(app, "workspace_context", lambda _query: "")
    session_id = app.create_chat_session(app.ChatSessionRequest())["session_id"]
    requested_messages = []

    def fake_call(messages):
        requested_messages.append(messages)
        return "Kobalt demistin."

    monkeypatch.setattr(app, "call_ollama", fake_call)
    app.chat(app.ChatRequest(message="En sevdiğim renk kobalt", session_id=session_id, memory=False))
    app.chat(app.ChatRequest(message="En sevdiğim renk neydi?", session_id=session_id, memory=False))

    followup_context = requested_messages[1]
    assert any(item["content"] == "En sevdiğim renk kobalt" for item in followup_context)
    assert any(item["content"] == "Kobalt demistin." for item in followup_context)


def test_chat_session_recalls_relevant_turns_older_than_recent_window(tmp_path: Path, monkeypatch):
    import app

    monkeypatch.setattr(app, "MEMORY_DB", tmp_path / "memory.db")
    monkeypatch.setattr(app, "workspace_context", lambda _query: "")
    session_id = app.create_chat_session(app.ChatSessionRequest())["session_id"]
    requested_messages = []

    def fake_call(messages):
        requested_messages.append(messages)
        return "Not edildi."

    monkeypatch.setattr(app, "call_ollama", fake_call)
    app.chat(app.ChatRequest(message="Proje gizli kod adi ORCHID", session_id=session_id, memory=False))
    for index in range(10):
        app.chat(app.ChatRequest(message=f"Bagimsiz konu {index} hakkinda bilgi ver", session_id=session_id, memory=False))
    app.chat(app.ChatRequest(message="ORCHID kod adini hatirliyor musun?", session_id=session_id, memory=False))

    assert any(item["content"] == "Proje gizli kod adi ORCHID" for item in requested_messages[-1])