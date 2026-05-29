# Chat Bundle Dispatch

Chat Bundles package summarized conversation context into a bounded Codex intake artifact.

They are for task dispatch, not evidence.

```text
ChatGPT conversation
-> summarized Chat Bundle
-> Bridge queue rows
-> Codex validation
-> status reports
```

## Files

```text
schemas/chat_bundle.schema.json
bundles/pending/
bundles/processed/
bundles/rejected/
scripts/create_chat_bundle.py
scripts/import_chat_bundle.py
reports/chat_bundle_status.json
```

## Create

```bash
python scripts/create_chat_bundle.py \
  --input chat_notes.md \
  --purpose "Continue Bridge service development" \
  --conversation-summary "Short bounded summary of the conversation." \
  --codex-instructions "Validate the bundle and stage requested tasks only." \
  --task "Build Chat Bundle ingestion and dispatch system"
```

The `--input` file is used for a source digest only. Do not place raw sensitive chat into the evidence layer.

## Import

```bash
python scripts/import_chat_bundle.py bundles/pending/chatbundle-example.json
```

Valid bundles are copied to:

```text
bundles/processed/
```

Rejected bundles are copied to:

```text
bundles/rejected/
```

Generated Bridge requests are appended to:

```text
queues/chatgpt_codex_work_queue.jsonl
```

## Safety Rules

- Do not ingest raw unfiltered chat as evidence.
- Do not treat chat claims as facts.
- Do not modify evidence outputs directly.
- Distinguish observed, inferred, unverified, and requested content.
- Preserve validation errors.

## Boundary

Chat Bundles are task context. They do not prove property, court, title, ownership, valuation, or misconduct claims.
