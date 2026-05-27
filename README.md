# Bridge

Codex-readable bridge repository for the OC Parcel Anomaly GIS Comparator.

## Purpose

This repository separates ChatGPT proposals from validated model evidence.

```text
ChatGPT proposals
-> validated request queue
-> Codex processing
-> refreshed evidence snapshots
-> ChatGPT-readable Gist raw JSON
```

## Evidence Discipline

- Do not write directly to model outputs from ChatGPT requests.
- Do not write directly to the public evidence Gist from ChatGPT.
- Treat user claims as notes or hypotheses unless independently sourced.
- Preserve provenance and validation errors.
- Use `unknown` instead of guessing.

## Primary Bridge Files

```text
manifests/codex_api_manifest.json
schemas/chatgpt_request.schema.json
exports/chatgpt_request_queue.jsonl
docs/GITHUB_CHATGPT_WRITEBACK.md
```

## Current Evidence Snapshot URLs

```text
https://gist.githubusercontent.com/GeorgeTownSabatical/ea83e2a96538900b5a0c0ca0b58b76b4/raw/local_summary.json
https://gist.githubusercontent.com/GeorgeTownSabatical/ea83e2a96538900b5a0c0ca0b58b76b4/raw/local_40128307.json
https://gist.githubusercontent.com/GeorgeTownSabatical/ea83e2a96538900b5a0c0ca0b58b76b4/raw/local_ranked25.json
https://gist.githubusercontent.com/GeorgeTownSabatical/ea83e2a96538900b5a0c0ca0b58b76b4/raw/local_pull_list100.json
```

## Standard Codex Flow

```bash
python scripts/import_chatgpt_github_requests.py --source local --input exports/chatgpt_request_queue.jsonl
python scripts/process_chatgpt_request_queue.py
python scripts/run_seed_cluster_40128307.py
python scripts/export_gis_api_snapshots.py
bash scripts/publish_gist_snapshots.sh
```

## Queue Discipline

```text
Evidence Gist = read-only published model state
Request Queue = proposed next actions
Codex = validator and publisher
```
