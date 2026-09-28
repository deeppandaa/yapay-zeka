DeepPanda Gemma 4 Developer Agent submission

This package adapts the LocalQwenAgent operating protocol to the Kaggle sandbox.
It intentionally contains no model weights or LoRA adapter. The competition
harness supplies Gemma 4 and evaluates the agent on repository patch success.

Included:
- agent.yaml: root Gemma 4 agent
- configs/sampling.yaml: competition-compatible deterministic reasoning and output budget
- prompts/: evidence-first planning, coding, and review instructions
- sub_agents/: code analysis and test review AgentTools invoked from the root tool list
- skills/repo_navigation/: local repository navigation protocol
- eval_config.yaml: nested per-task time, tool-call, and turn budgets
- validate_submission.py: strict local schema, include-path, skill, and size validation
- package_submission.py: reproducible, filtered submission.zip builder

The local Ollama, FastAPI, Windows, and SQLite runtime are not copied into the
submission because the Kaggle harness provides the allowed tools and workspace.
No untrained adapter is included; the competition-provided Gemma 4 base model is used.
