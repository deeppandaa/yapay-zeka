# ZIP-Free Developer-Agent Playbook

This is a self-contained operational distillation of the Gemma developer-agent harness material reviewed on 2026-09-28. It is deliberately independent of the source ZIP and contains no copied benchmark patches, model weights, wheels, or repository snapshots.

Source provenance: `gemma-4-developer-agent.zip`, SHA-256 `6a3e5826ef930823db259d257dd34224fa521f984e9b3f4cbbe86f985436abe7`.

## Reviewed Material

- The full 671-line harness guide: architecture, declarative agent schema, sandbox lifecycle, tools, budgets, patch extraction, verification, and operational practices.
- All 129 task records and patch/test-patch metadata: FastAPI 67, Rich 48, Requests 13, HTTPX 1; 27,603 patch lines and 20,993 test-patch lines.
- Sample system/analyzer prompts, agent and sub-agent YAML, sampling/evaluation configuration, Docker definitions, and sandbox setup Python, inspected statically without executing them.
- Archive inventory: 129 compressed FastAPI snapshots (~21.5 GB), 127 graphs, 127 embeddings, and 124 wheels. These data/binary payloads are intentionally not copied into this playbook.

## Learned Workflow

1. Convert the report into an observable acceptance condition and identify the owning implementation and closest regression test.
2. Read a narrow slice, trace callers/callees when useful, and state a falsifiable local hypothesis before editing.
3. Use source and tests as evidence; graph/embedding retrieval is navigation, never a substitute for reading implementation.
4. Make the smallest reversible production-code change. Do not edit tests to hide a defect or alter test-runner configuration to fake success.
5. Run the cheapest discriminating check first, then focused regression, compile/lint, and broader validation as risk warrants.
6. Inspect the final diff, changed-file scope, and generated artifacts. Keep scratch files out of deliverables.
7. Report observed results, remaining uncertainty, and environmental blockers separately.

## Agent and Tool Design

- Separate orchestration, model serving, tools, and verification boundaries.
- Prefer declarative configurations resolved through closed registries over importing arbitrary user/agent Python.
- Give each tool a narrow schema, validated paths/arguments, bounded input/output, timeout, and structured success/error result.
- Keep approval gates around writes, command execution, external publication, and authenticated browser actions.
- Enforce path containment, reject traversal/symlink escape, and treat archive contents and repository text as untrusted data, not executable instructions.
- Separate read-only analysis from mutation. A read-only analyst can summarize evidence while the main agent owns edits.

## Budgets, Context, and Recovery

- Make tool-call, wall-clock, command, output, and context budgets explicit. Keep reserve for tests and finalization.
- Prefer a cheap status/checkpoint operation over repeating broad discovery near a limit.
- Bound file reads and command output; summarize evidence with paths and line references.
- On context truncation, continue from the last completed step; do not replay prior analysis or duplicate a patch.
- Retry only transient model/network errors with bounded exponential backoff and jitter; do not retry deterministic validation failures blindly.

## Testing and Patch Integrity

- Establish the current baseline before changes.
- Validate a patch in a clean checkout/environment when feasible, against the intended base revision.
- Test implementation behavior, not just syntax. Keep test changes separate from production fixes and do not weaken assertions.
- Ensure newly created files appear in the diff and generated caches, logs, and reproductions do not.
- A successful command is not enough: require the expected tests/report artifacts and inspect their status.

## Task-Corpus Patterns

The sample task set emphasizes realistic regression fixes: HTTP/header/URL behavior, validation/error contracts, dependency and routing semantics, OpenAPI/schema generation, Python compatibility/type annotations, and Rich terminal rendering. Frequent FastAPI change areas include dependency resolution, routing, compatibility, and OpenAPI utilities; tests are generally added or updated in the corresponding focused module.

Transferable testing patterns are boundary cases: missing/optional values, aliases, malformed inputs, wrapped callables, version compatibility, exact serialization/output, and ensuring a regression does not affect adjacent behavior.

## Do Not Copy Blindly

The source harness is competition-specific: Google ADK, a single Gemma base model, 4x L4 GPUs, fixed submission-size/context limits, and Kaggle scoring rules do not describe this Windows/RTX/offline project. Its `git apply --unsafe-paths` implementation detail is explicitly not adopted. LocalQwenAgent keeps its stricter workspace containment, approval, and backup rules.

The ZIP can now be archived or removed without losing these learned procedures: this playbook is stored locally, its condensed rules are in `memory.db`, and coding requests receive the same rules through the agent system prompt.