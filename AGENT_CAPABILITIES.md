# LocalQwenAgent Capability Plan

## 1. Conversation and reasoning

- Intent classification: answer, learn, research, action request
- Structured plans before actions
- Local memory retrieval and explicit learning notes
- Source-aware answers with uncertainty

## 2. Coding workflow

- Inspect workspace files
- Explain existing architecture
- Generate modules, tests, README files, and project scaffolds
- Propose a diff before editing
- Read `WORKSPACE_ROOT` and, when `ALLOW_EXTERNAL_PATHS=on`, approved external paths except protected Windows/system directories
- Back up existing files before writes
- Run approved tests, typechecks, builds, and formatters
- Summarize changed files and remaining failures

## 3. Research workflow

- Public HTTP page extraction without an API token
- JavaScript page snapshots through Playwright Chromium
- Public GitHub repository and README research
- Source URL tracking
- Research summaries persisted to SQLite memory

## 4. File and media workflow

- PDF extraction and PDF append/export
- DOCX, PPTX, XLSX extraction
- Image upload for vision-capable local models
- FFmpeg audio extraction and video frame sampling
- Optional local faster-whisper transcription

## 5. Controlled execution

- Commands require explicit approval
- Allowed tools are limited to Python, Node, npm, and FFmpeg
- Commands run in the workspace with `shell=False`
- Approved file writes are backed up; protected Windows/system directories remain blocked
- No registry, service, system-folder, or destructive operation access by default

## 6. Not yet automatic

- Full model fine-tuning: requires a curated dataset and GPU training plan
- Arbitrary OS administration: intentionally blocked
- Package installation: must be requested and approved
- Browser login/private websites: requires the user to provide an authenticated session

## Operating contract

The agent must follow this loop:

1. Understand the request.
2. Classify intent.
3. Inspect relevant memory and workspace context.
4. Produce a concrete plan.
5. Ask approval for writes, installs, or command execution.
6. Execute the smallest approved steps.
7. Run validation.
8. Save a concise result and learning note.
