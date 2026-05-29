# GitHub ChatGPT Writeback

This repository is a proposal and validation bridge. It is not the evidence layer.

```text
ChatGPT may propose requests.
Codex validates requests.
Codex writes derived artifacts.
Published evidence snapshots are read-only from ChatGPT.
User claims remain hypotheses unless independently sourced.
```

## Queue

Primary local queue:

```text
exports/chatgpt_request_queue.jsonl
```

Schema:

```text
schemas/chatgpt_request.schema.json
```

Each JSONL row must include:

- `id`
- `type`
- `status`
- `created_at`
- `payload`
- `provenance`

## Evidence Boundary

ChatGPT writebacks are proposals. They do not directly alter:

- GIS model outputs,
- public evidence Gist snapshots,
- anomaly scores,
- title conclusions,
- ownership conclusions,
- allegations or misconduct findings.

Codex is responsible for validation, provenance preservation, and any derived artifact generation.

## Dry-Run Scripts

The scripts in this repository are intentionally conservative. They validate, stage, and report. They do not publish evidence unless an explicit future publishing configuration is added.

```bash
python scripts/import_chatgpt_github_requests.py --source local --input exports/chatgpt_request_queue.jsonl
python scripts/process_chatgpt_request_queue.py
python scripts/run_seed_cluster_40128307.py
python scripts/export_gis_api_snapshots.py
bash scripts/publish_gist_snapshots.sh
```

