---
name: repo_navigation
description: Navigate unfamiliar repositories safely before proposing a minimal tested patch.
---

# Repository Navigation

Use this skill before editing a repository issue.

1. Read the issue and identify the requested behavior.
2. Inspect the top-level tree and relevant build/test files.
3. Use code neighbors and semantic search to locate the controlling symbols.
4. Read the smallest nearby implementation slice and its tests.
5. Record one falsifiable hypothesis and one cheap validation.
6. Keep exploration local; do not map unrelated subsystems.

The root agent owns edits, validation, and patch submission. This skill only guides navigation and evidence gathering.
