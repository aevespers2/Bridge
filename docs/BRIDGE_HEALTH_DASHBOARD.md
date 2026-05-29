# Bridge Health Dashboard

The Bridge health dashboard is a compact operational status artifact for humans and ChatGPT.

It summarizes:

- queue counts,
- processed and rejected request counts,
- latest routine check status,
- Gist snapshot visibility,
- latest known test status,
- scheduler mode,
- task-ledger state,
- command-result counts,
- top active tasks.

## Generate

```bash
python scripts/export_bridge_health.py
```

Outputs:

```text
reports/bridge_health_latest.json
reports/bridge_health_latest.md
```

## Evidence Boundary

The health dashboard is operational status only. It does not prove claims, alter anomaly scores, mutate GIS evidence outputs, or publish the public evidence Gist.

Unknown values must stay `unknown` when the Bridge repo cannot verify them locally.

## Standard Review

Before queuing another task wave, review:

```text
reports/bridge_health_latest.md
reports/latest_bridge_run.json
queues/chatgpt_codex_processed.jsonl
queues/chatgpt_codex_rejected.jsonl
```

This reduces duplicate tasking and keeps the Bridge queue aligned with completed work.
