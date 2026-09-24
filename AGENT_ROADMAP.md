# LocalQwenAgent Roadmap

## Priority 1: Reliable coding agent

- Add a structured task record with intent, plan, approval, commands, changed files, tests, and result.
- Add diff preview before every workspace write.
- Add rollback endpoint for the last approved write.
- Add project-specific command profiles for Python, Node, and DeepPanda.
- Use the existing backup directory as the recovery source.

## Priority 2: Better memory

- Add memory search by keyword and source.
- Separate user preferences, project facts, procedures, research notes, and task history.
- Deduplicate repeated learning notes.
- Add memory export/import and a delete-by-source action.
- Add embeddings only after the SQLite baseline is stable.

## Priority 3: Live jobs

- Run long research, transcription, and tests as background jobs.
- Stream progress events to the browser.
- Add cancel/retry buttons and persistent job history.
- Store output artifacts and error logs per job.

## Priority 4: Local model independence

- Add a direct llama.cpp backend so Ollama is optional.
- Add model profiles for text, vision, and small fast tasks.
- Detect GPU memory and select a safe context/model profile.
- Keep Ollama as an optional compatibility backend.

## Priority 5: Multimodal analysis

- Send extracted video frames to a vision-capable local model.
- Combine Whisper transcript, frames, and timestamps into one report.
- Add OCR for scanned PDFs and screenshots.
- Export analysis to Markdown/PDF with source references.

## Safety contract

- No unrestricted operating-system control.
- Package installation and command execution require explicit approval.
- Workspace writes are backed up and limited to the configured workspace.
- Web research blocks private/local network addresses.
- Every automated action gets an audit record.
