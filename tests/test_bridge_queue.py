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
import export_bridge_health as bridge_health  # noqa: E402
import chat_bundle  # noqa: E402


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

    def test_bridge_health_dashboard_exports_operational_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            temp = Path(tempdir)
            queues = temp / "queues"
            exports = temp / "exports"
            reports = temp / "reports"
            queues.mkdir()
            exports.mkdir()
            reports.mkdir()

            work_queue = queues / "work.jsonl"
            processed = queues / "processed.jsonl"
            rejected = queues / "rejected.jsonl"
            local_processed = exports / "processed.jsonl"
            local_rejected = exports / "rejected.jsonl"
            latest_run = reports / "latest_bridge_run.json"
            routine = reports / "routine.json"
            repro = reports / "repro.json"
            ledger = reports / "ledger.jsonl"
            commands = reports / "commands.jsonl"
            json_output = reports / "health.json"
            md_output = reports / "health.md"

            work_queue.write_text(
                json.dumps(
                    {
                        "request_type": "codex_task",
                        "title": "Critical task",
                        "priority": "critical",
                        "status": "pending",
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            processed.write_text("", encoding="utf-8")
            rejected.write_text("", encoding="utf-8")
            local_processed.write_text(json.dumps({"id": "local-1", "status": "accepted"}) + "\n", encoding="utf-8")
            local_rejected.write_text("", encoding="utf-8")
            latest_run.write_text(
                json.dumps(
                    {
                        "blocked_count": 0,
                        "routine_check": {
                            "start_time": "2026-05-29T00:00:00+00:00",
                            "end_time": "2026-05-29T00:01:00+00:00",
                            "exit_status": "success",
                            "counts": {"commands": 1, "failed": 0, "succeeded": 1},
                        },
                        "command_results": {
                            "command_result_count": 1,
                            "executed_count": 1,
                            "failed_count": 0,
                            "rejected_count": 0,
                            "latest_results": [
                                {
                                    "command": "python -m unittest discover -s tests",
                                    "exit_code": 0,
                                    "completed_at": "2026-05-29T00:01:00+00:00",
                                }
                            ],
                        },
                    }
                ),
                encoding="utf-8",
            )
            routine.write_text("{}", encoding="utf-8")
            repro.write_text(json.dumps({"reproducible": True, "generated_at": "2026-05-29T00:01:00+00:00"}), encoding="utf-8")
            ledger.write_text(json.dumps({"id": "ledger-1"}) + "\n", encoding="utf-8")
            commands.write_text("", encoding="utf-8")

            old_paths = (
                bridge_health.WORK_QUEUE_PATH,
                bridge_health.PROCESSED_QUEUE_PATH,
                bridge_health.REJECTED_QUEUE_PATH,
                bridge_health.LOCAL_PROCESSED_PATH,
                bridge_health.LOCAL_REJECTED_PATH,
                bridge_health.LATEST_RUN_PATH,
                bridge_health.ROUTINE_CHECK_PATH,
                bridge_health.REPRO_REPORT_PATH,
                bridge_health.TASK_LEDGER_PATH,
                bridge_health.COMMAND_RESULTS_PATH,
                bridge_health.JSON_OUTPUT,
                bridge_health.MD_OUTPUT,
            )
            try:
                bridge_health.WORK_QUEUE_PATH = work_queue
                bridge_health.PROCESSED_QUEUE_PATH = processed
                bridge_health.REJECTED_QUEUE_PATH = rejected
                bridge_health.LOCAL_PROCESSED_PATH = local_processed
                bridge_health.LOCAL_REJECTED_PATH = local_rejected
                bridge_health.LATEST_RUN_PATH = latest_run
                bridge_health.ROUTINE_CHECK_PATH = routine
                bridge_health.REPRO_REPORT_PATH = repro
                bridge_health.TASK_LEDGER_PATH = ledger
                bridge_health.COMMAND_RESULTS_PATH = commands
                bridge_health.JSON_OUTPUT = json_output
                bridge_health.MD_OUTPUT = md_output
                bridge_health.main()
            finally:
                (
                    bridge_health.WORK_QUEUE_PATH,
                    bridge_health.PROCESSED_QUEUE_PATH,
                    bridge_health.REJECTED_QUEUE_PATH,
                    bridge_health.LOCAL_PROCESSED_PATH,
                    bridge_health.LOCAL_REJECTED_PATH,
                    bridge_health.LATEST_RUN_PATH,
                    bridge_health.ROUTINE_CHECK_PATH,
                    bridge_health.REPRO_REPORT_PATH,
                    bridge_health.TASK_LEDGER_PATH,
                    bridge_health.COMMAND_RESULTS_PATH,
                    bridge_health.JSON_OUTPUT,
                    bridge_health.MD_OUTPUT,
                ) = old_paths

            health = json.loads(json_output.read_text(encoding="utf-8"))
            self.assertEqual(health["overall_status"], "ok")
            self.assertEqual(health["queue_counts"]["work_queue"], 1)
            self.assertEqual(health["test_status"]["status"], "pass")
            self.assertEqual(health["top_active_tasks"][0]["title"], "Critical task")
            self.assertIn("Bridge Health Dashboard", md_output.read_text(encoding="utf-8"))

    def test_chat_bundle_import_dispatches_requests_without_evidence_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            temp = Path(tempdir)
            pending = temp / "pending"
            processed = temp / "processed"
            rejected = temp / "rejected"
            reports = temp / "reports"
            queue = temp / "queue.jsonl"
            source = temp / "notes.md"
            bundle_path = pending / "bundle.json"
            status_path = reports / "chat_bundle_status.json"
            source.write_text("summarized notes only\n", encoding="utf-8")
            bundle = chat_bundle.create_bundle(
                purpose="Continue Bridge service development",
                conversation_summary="Bounded summary with no raw evidence claims.",
                codex_instructions="Validate and stage requested tasks only.",
                input_path=source,
                tasks_requested=[
                    {
                        "title": "Build dispatch",
                        "instructions": "Create bundle dispatch.",
                        "priority": "high",
                        "acceptance_criteria": ["Bundle validates"],
                    }
                ],
                evidence_links=["reports/bridge_health_latest.json"],
            )
            chat_bundle.write_json(bundle_path, bundle)

            old_paths = (
                chat_bundle.PENDING_DIR,
                chat_bundle.PROCESSED_DIR,
                chat_bundle.REJECTED_DIR,
                chat_bundle.QUEUE_PATH,
                chat_bundle.STATUS_PATH,
            )
            try:
                chat_bundle.PENDING_DIR = pending
                chat_bundle.PROCESSED_DIR = processed
                chat_bundle.REJECTED_DIR = rejected
                chat_bundle.QUEUE_PATH = queue
                chat_bundle.STATUS_PATH = status_path
                status = chat_bundle.import_bundle(bundle_path)
            finally:
                (
                    chat_bundle.PENDING_DIR,
                    chat_bundle.PROCESSED_DIR,
                    chat_bundle.REJECTED_DIR,
                    chat_bundle.QUEUE_PATH,
                    chat_bundle.STATUS_PATH,
                ) = old_paths

            self.assertEqual(status["status"], "processed")
            self.assertEqual(status["requests_generated"], 1)
            self.assertTrue((processed / "bundle.json").exists())
            queued = json.loads(queue.read_text(encoding="utf-8").splitlines()[0])
            self.assertEqual(queued["title"], "Build dispatch")
            self.assertEqual(queued["source"], "chatgpt")
            self.assertIn("not proof", queued["evidence_boundary"])

    def test_chat_bundle_rejects_malformed_bundle(self) -> None:
        bundle = {
            "bundle_id": "bad-bundle",
            "created_by": "chatgpt",
            "created_at": "2026-05-29T00:00:00+00:00",
            "purpose": "",
            "conversation_summary": "ok",
            "tasks_requested": [{"title": ""}],
            "safety_boundaries": [],
            "codex_instructions": "ok",
        }

        errors = chat_bundle.validate_bundle(bundle)

        self.assertIn("purpose must contain at least 3 characters.", errors)
        self.assertIn("safety_boundaries must be a non-empty array.", errors)
        self.assertIn("tasks_requested[0].title is required.", errors)


if __name__ == "__main__":
    unittest.main()
