# Codex Bridge

Append requests to `codex_bridge/requests.jsonl`.

Each request is JSONL:

```json
{"id":"unique-id","type":"analysis_plan","status":"queued","payload":{"task":"...","outputs":["..."]}}
```

The GitHub Action runs `bridge_runner.py`, processes queued tasks, and writes outputs to:

```text
codex_bridge/output/
codex_bridge/status.json
```

This creates a controlled bridge:

```text
ChatGPT → GitHub queue → Codex runner → versioned outputs
```
