from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from bridge_queue import validate_row  # noqa: E402
from export_evidence_graph import build_graph  # noqa: E402
import export_reproducibility_report as reproducibility  # noqa: E402


class BridgeQueueTests(unittest.TestCase):
    def test_valid_seed_row(self) -> None:
        row = {
            "id": "request-1",
            "type": "codex_task",
            "status": "queued",
            "created_at": "2026-05-29T06:35:18Z",
            "payload": {"title": "Test"},
            "provenance": {"source": "test"},
        }

        self.assertEqual(validate_row(row), [])

    def test_missing_required_field_fails_clearly(self) -> None:
        row = {
            "id": "request-1",
            "type": "codex_task",
            "status": "queued",
            "created_at": "2026-05-29T06:35:18Z",
            "payload": {},
        }

        self.assertIn("Missing required field: provenance", validate_row(row))

    def test_invalid_jsonl_exits_nonzero(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            temp = Path(tempdir)
            queue = temp / "bad.jsonl"
            queue.write_text("{bad json}\n", encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "process_chatgpt_request_queue.py"),
                    "--input",
                    str(queue),
                    "--processed-output",
                    str(temp / "processed.jsonl"),
                    "--rejected-output",
                    str(temp / "rejected.jsonl"),
                ],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertNotEqual(result.returncode, 0)
            rejected = (temp / "rejected.jsonl").read_text(encoding="utf-8")
            self.assertIn("Invalid JSON", rejected)

    def test_queue_processing_writes_accepted_output(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            temp = Path(tempdir)
            queue = temp / "queue.jsonl"
            row = {
                "id": "request-1",
                "type": "codex_task",
                "status": "queued",
                "created_at": "2026-05-29T06:35:18Z",
                "payload": {"title": "Test"},
                "provenance": {"source": "test"},
            }
            queue.write_text(json.dumps(row) + "\n", encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "process_chatgpt_request_queue.py"),
                    "--input",
                    str(queue),
                    "--processed-output",
                    str(temp / "processed.jsonl"),
                    "--rejected-output",
                    str(temp / "rejected.jsonl"),
                ],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            processed = json.loads((temp / "processed.jsonl").read_text(encoding="utf-8").splitlines()[0])
            self.assertEqual(processed["status"], "accepted")
            self.assertEqual(processed["validation_status"], "PASS")
            self.assertEqual(processed["validation_errors"], [])

    def test_validation_status_is_limited_to_three_values(self) -> None:
        row = {
            "id": "request-1",
            "type": "codex_task",
            "status": "queued",
            "created_at": "2026-05-29T06:35:18Z",
            "payload": {"title": "Test"},
            "provenance": {"source": "test"},
            "validation_status": "MAYBE",
        }

        self.assertIn("Unsupported validation_status: MAYBE", validate_row(row))

    def test_evidence_graph_links_observation_claim_and_validation(self) -> None:
        graph = build_graph(
            [
                {
                    "id": "obs-1",
                    "observation": "document mentions parcel",
                    "document_refs": ["doc-1"],
                    "subject_refs": ["parcel:401-283-07"],
                    "provenance": {"source": "test"},
                }
            ],
            [
                {
                    "id": "claim-1",
                    "claim": "parcel appears unusual",
                    "observation_refs": ["obs-1"],
                    "provenance": {"source": "test"},
                }
            ],
            [
                {
                    "id": "val-1",
                    "target_id": "claim-1",
                    "validation_status": "UNKNOWN",
                    "supporting_refs": ["obs-1"],
                    "contradicting_refs": [],
                    "provenance": {"source": "test"},
                }
            ],
        )

        edge_types = {edge["type"] for edge in graph["edges"]}
        node_types = {node["type"] for node in graph["nodes"]}
        self.assertIn("observation", node_types)
        self.assertIn("claim", node_types)
        self.assertIn("validation", node_types)
        self.assertIn("supports_claim_context", edge_types)
        self.assertIn("validates", edge_types)

    def test_reproducibility_report_exports_review_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            temp = Path(tempdir)
            reports = temp / "reports"
            exports = temp / "exports"
            docs = temp / "docs" / "evidence-graph"
            reports.mkdir(parents=True)
            exports.mkdir(parents=True)
            docs.mkdir(parents=True)

            graph_path = reports / "evidence_graph.json"
            queue_path = exports / "queue.jsonl"
            processed_path = exports / "processed.jsonl"
            rejected_path = exports / "rejected.jsonl"
            json_output = reports / "reproducibility_report.json"
            md_output = reports / "reproducibility_report.md"
            page_output = docs / "index.html"

            graph_path.write_text(
                json.dumps(
                    {
                        "nodes": [
                            {
                                "id": "obs-1",
                                "type": "observation",
                                "label": "observed document",
                                "payload": {"document_refs": ["doc-1"]},
                                "provenance": {"validation_status": "PASS"},
                            },
                            {
                                "id": "claim-1",
                                "type": "claim",
                                "label": "hypothesis",
                                "payload": {"claim": "needs validation", "status": "hypothesis"},
                                "provenance": {"validation_status": "UNKNOWN"},
                            },
                        ],
                        "edges": [{"source": "obs-1", "target": "claim-1", "type": "supports_claim_context"}],
                        "provenance": {"source": "test"},
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            queue_path.write_text(json.dumps({"id": "request-1"}) + "\n", encoding="utf-8")
            processed_path.write_text(json.dumps({"id": "request-1", "validation_status": "PASS"}) + "\n", encoding="utf-8")
            rejected_path.write_text("", encoding="utf-8")

            old_paths = (
                reproducibility.GRAPH_PATH,
                reproducibility.QUEUE_PATH,
                reproducibility.PROCESSED_PATH,
                reproducibility.REJECTED_PATH,
                reproducibility.JSON_OUTPUT,
                reproducibility.MD_OUTPUT,
                reproducibility.PAGE_OUTPUT,
            )
            try:
                reproducibility.GRAPH_PATH = graph_path
                reproducibility.QUEUE_PATH = queue_path
                reproducibility.PROCESSED_PATH = processed_path
                reproducibility.REJECTED_PATH = rejected_path
                reproducibility.JSON_OUTPUT = json_output
                reproducibility.MD_OUTPUT = md_output
                reproducibility.PAGE_OUTPUT = page_output
                reproducibility.main()
            finally:
                (
                    reproducibility.GRAPH_PATH,
                    reproducibility.QUEUE_PATH,
                    reproducibility.PROCESSED_PATH,
                    reproducibility.REJECTED_PATH,
                    reproducibility.JSON_OUTPUT,
                    reproducibility.MD_OUTPUT,
                    reproducibility.PAGE_OUTPUT,
                ) = old_paths

            report = json.loads(json_output.read_text(encoding="utf-8"))
            self.assertTrue(report["reproducible"])
            self.assertEqual(report["validation_counts"]["UNKNOWN"], 1)
            self.assertIn("doc-1", report["required_sources"])
            self.assertIn("python scripts/export_reproducibility_report.py", report["commands"])
            self.assertIn("Bridge Evidence Graph Review", page_output.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
