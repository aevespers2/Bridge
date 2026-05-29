# Codex Bridge Protocol

## Purpose

This repository acts as a controlled interface between:

```text
ChatGPT
↔ Bridge Repo
↔ Codex
↔ GIS / anomaly model
↔ published evidence snapshots
```

## Design Principles

- Queue-first architecture
- No direct evidence modification from ChatGPT
- Provenance-preserving workflow
- Validation before execution
- Reproducible Codex tasks
- Audit trail retention

## Core Files

```text
schemas/chatgpt_codex_request.schema.json
queues/chatgpt_codex_work_queue.jsonl
queues/chatgpt_codex_processed.jsonl
queues/chatgpt_codex_rejected.jsonl
schemas/chat_bundle.schema.json
bundles/pending/
bundles/processed/
bundles/rejected/
```

## Chat Bundle Dispatch

Chat Bundles carry bounded conversation summaries, decisions, open questions, evidence links, and requested tasks into Bridge. They are task context only, not evidence.

```bash
python scripts/create_chat_bundle.py --purpose "..." --conversation-summary "..." --codex-instructions "..." --task "..."
python scripts/import_chat_bundle.py bundles/pending/chatbundle-example.json
```

See:

```text
docs/CHAT_BUNDLE_DISPATCH.md
```

## Queue Semantics

### pending
Awaiting Codex ingestion.

### accepted
Validated and approved for execution.

### processing
Codex actively running task.

### processed
Completed successfully.

### rejected
Validation failed.

### blocked
Waiting on external dependency.

## Codex Consumption Loop

Codex should:

1. Pull latest queue file.
2. Validate each JSONL row against schema.
3. Reject malformed entries.
4. Execute accepted tasks.
5. Write status updates.
6. Regenerate outputs.
7. Publish refreshed Gist snapshots.
8. Preserve provenance.

## Safety Rules

- Do not allow ChatGPT to directly alter outputs/gis_model/.
- Do not let queue entries overwrite evidence artifacts.
- Treat allegations as hypotheses unless independently sourced.
- Preserve rejected rows with validation_errors.
- Never silently merge entities.

## Recommended Codex Poll Command

```bash
python scripts/process_chatgpt_request_queue.py
```

## Recommended Full Refresh

```bash
python scripts/process_chatgpt_request_queue.py
python scripts/run_seed_cluster_40128307.py
python scripts/export_gis_api_snapshots.py
bash scripts/publish_gist_snapshots.sh
```
