DeepPanda Gemma 4 Developer Agent submission

This package adapts the LocalQwenAgent operating protocol to the Kaggle sandbox.
It intentionally contains no model weights or LoRA adapter. The competition
harness supplies Gemma 4 and evaluates the agent on repository patch success.

Included:
- agent.yaml: root Gemma 4 agent
- prompts/: evidence-first planning, coding, and review instructions
- sub_agents/: code analysis and test review roles
- skills/repo_navigation/: local repository navigation protocol
- eval_config.yaml: conservative time/output settings

The local Ollama, FastAPI, Windows, and SQLite runtime are not copied into the
submission because the Kaggle harness provides the allowed tools and workspace.
