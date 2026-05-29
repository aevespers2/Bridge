#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
GRAPH_PATH = ROOT / "reports" / "evidence_graph.json"
QUEUE_PATH = ROOT / "exports" / "chatgpt_request_queue.jsonl"
PROCESSED_PATH = ROOT / "exports" / "chatgpt_request_queue_processed.jsonl"
REJECTED_PATH = ROOT / "exports" / "chatgpt_request_queue_rejected.jsonl"
JSON_OUTPUT = ROOT / "reports" / "reproducibility_report.json"
MD_OUTPUT = ROOT / "reports" / "reproducibility_report.md"
PAGE_OUTPUT = ROOT / "docs" / "evidence-graph" / "index.html"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    parsed = json.loads(path.read_text(encoding="utf-8"))
    return parsed if isinstance(parsed, dict) else {}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        parsed = json.loads(line)
        if isinstance(parsed, dict):
            rows.append(parsed)
    return rows


def status_counts(nodes: list[dict[str, Any]], processed: list[dict[str, Any]], rejected: list[dict[str, Any]]) -> dict[str, int]:
    counts = {"PASS": 0, "FAIL": 0, "UNKNOWN": 0}
    for node in nodes:
        payload = node.get("payload", {})
        provenance = node.get("provenance", {})
        status = payload.get("validation_status") or provenance.get("validation_status")
        if status in counts:
            counts[status] += 1
    for row in processed:
        status = row.get("validation_status")
        if status in counts:
            counts[status] += 1
    for row in rejected:
        counts["FAIL"] += 1
    return counts


def build_report() -> dict[str, Any]:
    graph = read_json(GRAPH_PATH)
    queue = read_jsonl(QUEUE_PATH)
    processed = read_jsonl(PROCESSED_PATH)
    rejected = read_jsonl(REJECTED_PATH)
    nodes = graph.get("nodes", []) if isinstance(graph.get("nodes"), list) else []
    edges = graph.get("edges", []) if isinstance(graph.get("edges"), list) else []
    unknown_claims = [
        node
        for node in nodes
        if node.get("type") == "claim"
        and (
            node.get("payload", {}).get("status") in {"hypothesis", "unresolved", "under_review"}
            or node.get("provenance", {}).get("validation_status") == "UNKNOWN"
        )
    ]
    observed_outputs = [node for node in nodes if node.get("type") in {"observation", "document"}]
    derived_outputs = [node for node in nodes if node.get("type") in {"claim", "validation"}]
    required_sources = sorted(
        {
            str(ref)
            for node in nodes
            for ref in node.get("payload", {}).get("document_refs", []) + node.get("payload", {}).get("supporting_refs", [])
        }
        | {
            "exports/chatgpt_request_queue.jsonl",
            "exports/chatgpt_request_queue_processed.jsonl",
            "data/observations.jsonl",
            "data/claims.jsonl",
            "data/validation_records.jsonl",
        }
    )
    commands = [
        "python scripts/import_chatgpt_github_requests.py --source local --input exports/chatgpt_request_queue.jsonl",
        "python scripts/process_chatgpt_request_queue.py",
        "python scripts/export_evidence_graph.py",
        "python scripts/export_reproducibility_report.py",
        "python -m unittest discover -s tests",
    ]
    return {
        "schema": "bridge_reproducibility_report.v1",
        "generated_at": utc_now(),
        "reproducible": len(rejected) == 0 and bool(graph),
        "required_sources": required_sources,
        "commands": commands,
        "validation_counts": status_counts(nodes, processed, rejected),
        "queue_counts": {
            "queued": len(queue),
            "processed": len(processed),
            "rejected": len(rejected),
        },
        "graph_counts": {
            "nodes": len(nodes),
            "edges": len(edges),
            "node_types": sorted({str(node.get("type")) for node in nodes}),
            "edge_types": sorted({str(edge.get("type")) for edge in edges}),
        },
        "unknown_claims": [
            {
                "id": node.get("id"),
                "claim": node.get("payload", {}).get("claim", node.get("label", "")),
                "status": node.get("payload", {}).get("status", "unknown"),
                "validation_status": node.get("provenance", {}).get("validation_status", "UNKNOWN"),
            }
            for node in unknown_claims
        ],
        "derived_vs_observed": {
            "observed_node_ids": [node.get("id") for node in observed_outputs],
            "derived_node_ids": [node.get("id") for node in derived_outputs],
        },
        "evidence_boundary": "Reproducibility report describes commands and sources; it does not prove claims or mutate evidence snapshots.",
    }


def markdown(report: dict[str, Any]) -> str:
    unknown = report["unknown_claims"]
    unknown_lines = "\n".join(f"- `{row['id']}`: {row['claim']} ({row['validation_status']})" for row in unknown) or "- none"
    source_lines = "\n".join(f"- `{source}`" for source in report["required_sources"])
    command_lines = "\n".join(f"```bash\n{command}\n```" for command in report["commands"])
    return f"""# Bridge Reproducibility Report

Generated: `{report['generated_at']}`

Reproducible from current repository state: `{report['reproducible']}`

## Validation Counts

```json
{json.dumps(report['validation_counts'], indent=2, sort_keys=True)}
```

## Required Sources

{source_lines}

## Commands

{command_lines}

## UNKNOWN Claims

{unknown_lines}

## Boundary

{report['evidence_boundary']}
"""


def html_page(report: dict[str, Any], graph: dict[str, Any]) -> str:
    data = json.dumps({"report": report, "graph": graph}, sort_keys=True).replace("<", "\\u003c")
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Bridge Evidence Graph Review</title>
  <style>
    body {{ margin: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: #f7f9fb; color: #1f2933; }}
    main {{ max-width: 1120px; margin: 0 auto; padding: 20px; }}
    h1 {{ font-size: clamp(30px, 5vw, 54px); margin: 0 0 8px; letter-spacing: 0; }}
    .grid {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; margin: 18px 0; }}
    .card {{ background: #fff; border: 1px solid #d8dee6; border-radius: 8px; padding: 14px; }}
    .status {{ display: inline-block; padding: 3px 8px; border-radius: 999px; font-weight: 750; }}
    .PASS {{ background: #dcfce7; color: #166534; }}
    .FAIL {{ background: #fee2e2; color: #991b1b; }}
    .UNKNOWN {{ background: #fef3c7; color: #92400e; }}
    pre {{ overflow-x: auto; background: #101820; color: #f8fbff; border-radius: 8px; padding: 12px; }}
    table {{ width: 100%; border-collapse: collapse; background: #fff; }}
    th, td {{ text-align: left; border-bottom: 1px solid #d8dee6; padding: 8px; vertical-align: top; }}
    @media (max-width: 800px) {{ .grid {{ grid-template-columns: 1fr; }} }}
  </style>
</head>
<body>
<main>
  <h1>Bridge Evidence Graph Review</h1>
  <p>Static review surface for observations, claims, validation records, provenance, and reproducibility. Claims remain hypotheses unless validated by independent sources.</p>
  <div class="grid" id="counts"></div>
  <h2>UNKNOWN Claims</h2>
  <table id="unknown"><thead><tr><th>ID</th><th>Claim</th><th>Status</th></tr></thead><tbody></tbody></table>
  <h2>Nodes</h2>
  <table id="nodes"><thead><tr><th>Type</th><th>ID</th><th>Label</th><th>Validation</th></tr></thead><tbody></tbody></table>
  <h2>Edges By Type</h2>
  <pre id="edges"></pre>
  <h2>Provenance</h2>
  <pre id="provenance"></pre>
</main>
<script id="bridge-data" type="application/json">{data}</script>
<script>
const data = JSON.parse(document.getElementById('bridge-data').textContent);
const report = data.report;
const graph = data.graph;
function appendTextCell(row, value) {{
  const cell = document.createElement('td');
  cell.textContent = value == null ? '' : String(value);
  row.appendChild(cell);
  return cell;
}}
function appendStatusCell(row, value) {{
  const cell = document.createElement('td');
  const status = value || 'UNKNOWN';
  const badge = document.createElement('span');
  badge.className = `status ${{status}}`;
  badge.textContent = status;
  cell.appendChild(badge);
  row.appendChild(cell);
  return cell;
}}
const counts = document.getElementById('counts');
for (const [key, value] of Object.entries(report.validation_counts)) {{
  const section = document.createElement('section');
  section.className = 'card';
  const heading = document.createElement('h2');
  heading.textContent = key;
  const count = document.createElement('p');
  count.className = `status ${{key}}`;
  count.textContent = value;
  section.append(heading, count);
  counts.appendChild(section);
}}
for (const [label, value] of [['Nodes', report.graph_counts.nodes], ['Edges', report.graph_counts.edges]]) {{
  const section = document.createElement('section');
  section.className = 'card';
  const heading = document.createElement('h2');
  heading.textContent = label;
  const count = document.createElement('p');
  count.textContent = value;
  section.append(heading, count);
  counts.appendChild(section);
}}
const unknownBody = document.querySelector('#unknown tbody');
for (const row of report.unknown_claims) {{
  const tr = document.createElement('tr');
  appendTextCell(tr, row.id);
  appendTextCell(tr, row.claim);
  appendStatusCell(tr, row.validation_status);
  unknownBody.appendChild(tr);
}}
const nodeBody = document.querySelector('#nodes tbody');
for (const node of graph.nodes || []) {{
  const validation = node.payload?.validation_status || node.provenance?.validation_status || 'UNKNOWN';
  const tr = document.createElement('tr');
  appendTextCell(tr, node.type);
  appendTextCell(tr, node.id);
  appendTextCell(tr, node.label || '');
  appendStatusCell(tr, validation);
  nodeBody.appendChild(tr);
}}
const byType = {{}};
for (const edge of graph.edges || []) {{
  byType[edge.type] ||= [];
  byType[edge.type].push(`${{edge.source}} -> ${{edge.target}}`);
}}
document.getElementById('edges').textContent = JSON.stringify(byType, null, 2);
document.getElementById('provenance').textContent = JSON.stringify({{report: report.evidence_boundary, graph: graph.provenance}}, null, 2);
</script>
</body>
</html>
"""


def main() -> None:
    report = build_report()
    graph = read_json(GRAPH_PATH)
    JSON_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    PAGE_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    JSON_OUTPUT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    MD_OUTPUT.write_text(markdown(report), encoding="utf-8")
    PAGE_OUTPUT.write_text(html_page(report, graph), encoding="utf-8")
    print(json.dumps({"json": str(JSON_OUTPUT), "markdown": str(MD_OUTPUT), "page": str(PAGE_OUTPUT)}, sort_keys=True))


if __name__ == "__main__":
    main()
