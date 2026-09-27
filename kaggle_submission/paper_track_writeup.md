# Evidence-First Local Coding Agents
## Safe repository navigation and minimal tested patches on consumer hardware

### Abstract

Autonomous software-engineering agents often fail before code generation: they inspect too broadly, choose the wrong control path, change unrelated files, or stop without executable validation. This project presents an evidence-first protocol for local coding agents. The protocol separates repository navigation, minimal patch construction, and validation; records task provenance; uses semantic code context; and constrains filesystem and command access. We implemented the protocol in LocalQwenAgent, an offline-capable coding workspace built around Ollama, FastAPI, SQLite, workspace-scoped tools, and explicit approval gates. We then prepared a Gemma 4-compatible agent configuration for the Google Gemma 4 Developer Agent Competition.

The central research question is whether explicit hypothesis-driven navigation and validation improve patch reliability for models running on consumer hardware. The contribution is a reproducible agent protocol and evaluation design rather than a claim of completed fine-tuning. The system is designed to compare a baseline local coding agent against a treatment agent with repository navigation skills, code-neighbor retrieval, diff previews, task records, and post-patch tests.

### 1. Introduction

Software engineering tasks are situated in large, changing repositories. A useful coding agent must understand the repository, identify the implementation surface that controls the behavior, make a compatible change, and demonstrate that the change works. A model that writes plausible code without this loop can produce a locally attractive but incorrect patch.

Local models offer privacy, lower recurring cost, and offline operation, but their context and compute budgets are limited. The practical question is therefore not only how to make a model larger, but how to spend a limited interaction budget. LocalQwenAgent explores a protocol that makes evidence gathering explicit and bounded. It is intended for ordinary developer hardware, including a laptop with an 8 GB GPU, while remaining compatible with a larger harness-provided model such as Gemma 4.

This work targets three failure modes: wrong-path exploration, uncontrolled modification, and unsupported completion claims. The protocol addresses them with a falsifiable local hypothesis, a smallest-plausible edit, and an executable check selected before implementation.

### 2. Related Work and Positioning

The approach is related to SWE-bench-style repository repair, tool-using language agents, retrieval-augmented generation, parameter-efficient fine-tuning, and code-graph retrieval. Repository repair benchmarks evaluate whether a patch fixes an issue and passes project validation. Tool-using agents extend language models with file and command operations. Retrieval systems reduce the amount of irrelevant repository context. PEFT methods allow an open model to specialize without updating all model weights.

LocalQwenAgent combines these directions into an operational contract. It does not claim that a prompt protocol replaces fine-tuning. Instead, it provides a reproducible harness for measuring behavioral improvements before and after prompt, tool, retrieval, or adapter changes. The design also follows provenance and frozen-suite practices: each result should identify the source commit, model revision, prompt revision, evaluation suite, timestamp, and critical source hashes.

### 3. Agent Protocol

The treatment agent follows this loop:

1. Understand the issue and classify the requested behavior.
2. Inspect the repository tree and nearby tests.
3. State one falsifiable hypothesis about the controlling code path.
4. Use code-neighbor and semantic retrieval only to resolve the local uncertainty.
5. Propose the smallest compatible patch.
6. Run the cheapest relevant validation.
7. Repair the same slice if validation exposes a local defect.
8. Review the final diff and report files, tests, and remaining uncertainty.

The protocol distinguishes wiring code from deciding code. When an endpoint, registry, or forwarding function does not determine behavior, the agent takes one nearby hop to the function that computes or mutates the result. This keeps the context budget focused and makes the reasoning auditable without exposing hidden chain-of-thought.

### 4. System Implementation

LocalQwenAgent provides a browser workspace and an OpenAI-compatible local bridge. The application uses FastAPI for the service layer, Ollama for local model inference, SQLite for memory and task records, and Python tools for file and media workflows. The agent can inspect project files, prepare code and tests, preview diffs, write only inside a configured workspace, back up existing files, run approved commands, and roll back a completed write.

The memory layer supports explicit user notes, source and project categories, keyword retrieval, RAG context, embedding-based semantic search, export/import, and GitHub documentation indexing. The memory database is deliberately separated from the source repository and model weights. This separation prevents large or private runtime data from entering a competition submission.

The competition adaptation replaces local FastAPI and Ollama dependencies with the harness-provided sandbox tools. The root agent uses the supported Gemma 4 model identifier, while the prompts and repository-navigation skill preserve the evidence-first protocol. Two sub-agents are defined: a read-only code analyzer and a test reviewer. No LoRA adapter is included because no trained adapter has been claimed; the configuration is honest about using the competition-provided base model.

### 5. Experimental Design

We will evaluate a baseline and treatment configuration on a frozen task suite. The baseline receives the issue and standard repository tools. The treatment additionally receives the repository-navigation skill, semantic context retrieval, explicit hypothesis formation, diff-oriented editing, and validation protocol.

The primary metric is patch pass rate: the percentage of repository issues for which the submitted patch applies and the validation tests pass. Secondary metrics are first-attempt pass rate, test pass rate, number of tool calls, wall-clock time, token budget, unrelated-file count, and recovery rate after a failed validation. We will record all metrics with provenance metadata.

The local development suite currently includes intent classification, plan quality, research intent, persistent learning intent, workspace path safety, backup-before-write, diff preview, rollback, and importability tests. The next benchmark expansion should add real repository issues with deterministic validation, because intent tests alone cannot establish software-engineering success.

### 6. Ablations

The following ablations isolate the value of each component:

- Remove the falsifiable-hypothesis requirement.
- Remove semantic code context while preserving file search.
- Remove the test-review sub-agent.
- Remove diff preview and compare unrelated-file changes.
- Replace bounded workspace tools with unrestricted command access in a controlled research environment.
- Compare the local Qwen baseline against the Gemma 4 harness configuration.

The expected result is not that every component improves every task. The purpose is to identify which controls improve reliability under a fixed time and tool budget.

### 7. Reproducibility and Safety

The source implementation is publicly available at https://github.com/deeppandaa/yapay-zeka. Reproduction requires the source commit, model identifier, prompt files, evaluation cases, environment description, and generated result artifacts. Model weights, credentials, local memory, and runtime caches are excluded from the competition package.

The agent rejects workspace traversal, keeps writes inside the workspace, backs up existing files, requires explicit approval for commands, and uses shell-free subprocess execution. Public research blocks local and private network addresses. These controls are part of the research question: reliability includes making a useful change without silently exceeding the agent's authority.

### 8. Limitations

This submission does not claim completed Gemma 4 fine-tuning or a statistically complete benchmark. The current local model is Qwen through Ollama, while the competition harness requires Gemma 4. The 8 GB local GPU is suitable for developing the protocol and running small local models, but not for hosting the required 31B Gemma variant. The competition package therefore separates the local reference implementation from the Gemma-compatible configuration.

The task suite must be expanded with public repository issues and repeated runs before quantitative conclusions are reported. Tool-call and token measurements also depend on the harness implementation. Finally, safe approval gates may trade a small amount of autonomy for auditability; the correct trade-off should be measured rather than assumed.

### 9. Conclusion

Evidence-first navigation turns a coding agent from a code generator into a controlled repair workflow. LocalQwenAgent provides a working reference implementation with persistent memory, workspace safety, provenance-oriented evaluation, and multimodal project tooling. Its Gemma 4 adaptation packages the protocol as prompts, sub-agents, and a repository-navigation skill that can be evaluated by the competition harness. The resulting research direction is practical: improve agent reliability by controlling context, authority, and validation, then measure each intervention on frozen repository tasks.

### Reproducibility checklist

- Public source repository: https://github.com/deeppandaa/yapay-zeka
- Gemma 4 agent package: `DeepPanda-Gemma4-submission.zip`
- Frozen local cases: `evaluation_cases.json`
- Local evaluator: `run_evaluation.py`
- Protocol implementation: `agent_orchestrator.py` and `agent_tools.py`
- Runtime data and memory intentionally excluded from the submission archive
