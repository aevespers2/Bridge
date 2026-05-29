# Bridge Reproducibility Report

Generated: `2026-05-29T08:45:09.626348+00:00`

Reproducible from current repository state: `True`

## Validation Counts

```json
{
  "FAIL": 0,
  "PASS": 4,
  "UNKNOWN": 1
}
```

## Required Sources

- `.github/workflows/validate-bridge.yml`
- `data/claims.jsonl`
- `data/observations.jsonl`
- `data/validation_records.jsonl`
- `exports/chatgpt_request_queue.jsonl`
- `exports/chatgpt_request_queue_processed.jsonl`
- `https://github.com/aevespers2/Bridge/issues/1`

## Commands

```bash
python scripts/import_chatgpt_github_requests.py --source local --input exports/chatgpt_request_queue.jsonl
```
```bash
python scripts/process_chatgpt_request_queue.py
```
```bash
python scripts/export_evidence_graph.py
```
```bash
python scripts/export_reproducibility_report.py
```
```bash
python -m unittest discover -s tests
```

## UNKNOWN Claims

- `claim-bridge-001`: The Bridge repository should operate as an epistemic firewall separating observations, claims, validation, evidence graph, and published state. (UNKNOWN)

## Boundary

Reproducibility report describes commands and sources; it does not prove claims or mutate evidence snapshots.
