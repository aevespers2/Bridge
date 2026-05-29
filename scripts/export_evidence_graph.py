#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OBSERVATIONS = ROOT / "data" / "observations.jsonl"
DEFAULT_CLAIMS = ROOT / "data" / "claims.jsonl"
DEFAULT_VALIDATIONS = ROOT / "data" / "validation_records.jsonl"
DEFAULT_OUTPUT = ROOT / "reports" / "evidence_graph.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


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


def node(node_id: str, node_type: str, label: str, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": node_id,
        "type": node_type,
        "label": label,
        "payload": payload,
        "provenance": payload.get("provenance", {}),
    }


def edge(source: str, target: str, edge_type: str, provenance: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "source": source,
        "target": target,
        "type": edge_type,
        "provenance": provenance or {},
    }


def build_graph(observations: list[dict[str, Any]], claims: list[dict[str, Any]], validations: list[dict[str, Any]]) -> dict[str, Any]:
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    for observation in observations:
        obs_id = observation["id"]
        nodes.append(node(obs_id, "observation", observation.get("observation", "")[:120], observation))
        for doc_ref in observation.get("document_refs", []):
            doc_id = f"document:{doc_ref}"
            nodes.append(node(doc_id, "document", str(doc_ref), {"id": doc_id, "ref": doc_ref, "provenance": observation.get("provenance", {})}))
            edges.append(edge(doc_id, obs_id, "documents", observation.get("provenance", {})))
        for subject_ref in observation.get("subject_refs", []):
            edges.append(edge(obs_id, subject_ref, "observes", observation.get("provenance", {})))
    for claim in claims:
        claim_id = claim["id"]
        nodes.append(node(claim_id, "claim", claim.get("claim", "")[:120], claim))
        for obs_ref in claim.get("observation_refs", []):
            edges.append(edge(obs_ref, claim_id, "supports_claim_context", claim.get("provenance", {})))
    for validation in validations:
        val_id = validation["id"]
        nodes.append(node(val_id, "validation", validation.get("validation_status", "UNKNOWN"), validation))
        edges.append(edge(val_id, validation.get("target_id", ""), "validates", validation.get("provenance", {})))
        for ref in validation.get("supporting_refs", []):
            edges.append(edge(str(ref), val_id, "supports_validation", validation.get("provenance", {})))
        for ref in validation.get("contradicting_refs", []):
            edges.append(edge(str(ref), val_id, "contradicts_validation", validation.get("provenance", {})))
    seen: set[str] = set()
    unique_nodes: list[dict[str, Any]] = []
    for item in nodes:
        if item["id"] in seen:
            continue
        seen.add(item["id"])
        unique_nodes.append(item)
    return {
        "schema": "bridge_evidence_graph.v1",
        "generated_at": utc_now(),
        "nodes": unique_nodes,
        "edges": edges,
        "provenance": {
            "generated_by": "codex",
            "producer": "scripts/export_evidence_graph.py",
            "evidence_boundary": "Graph links observations, claims, and validation records; it does not convert hypotheses into proof.",
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export the Bridge evidence graph.")
    parser.add_argument("--observations", default=str(DEFAULT_OBSERVATIONS))
    parser.add_argument("--claims", default=str(DEFAULT_CLAIMS))
    parser.add_argument("--validations", default=str(DEFAULT_VALIDATIONS))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    graph = build_graph(
        read_jsonl(Path(args.observations)),
        read_jsonl(Path(args.claims)),
        read_jsonl(Path(args.validations)),
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(graph, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output), "nodes": len(graph["nodes"]), "edges": len(graph["edges"])}, sort_keys=True))


if __name__ == "__main__":
    main()
