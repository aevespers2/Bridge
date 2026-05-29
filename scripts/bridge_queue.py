from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
QUEUE_PATH = ROOT / "exports" / "chatgpt_request_queue.jsonl"
PROCESSED_PATH = ROOT / "exports" / "chatgpt_request_queue_processed.jsonl"
REJECTED_PATH = ROOT / "exports" / "chatgpt_request_queue_rejected.jsonl"

ALLOWED_TYPES = {
    "codex_task",
    "add_note",
    "review_apn",
    "add_apn",
    "link_apns",
    "request_office_pull",
    "refresh_snapshots",
    "publish_gist",
    "run_tests",
    "mark_resolved",
}
ALLOWED_STATUSES = {"queued", "accepted", "rejected", "processing", "done", "error"}
VALIDATION_STATUSES = {"PASS", "FAIL", "UNKNOWN"}
REQUIRED_FIELDS = ["id", "type", "status", "created_at", "payload", "provenance"]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_jsonl(path: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    rejects: list[dict[str, Any]] = []
    if not path.exists():
        return rows, [{"line_number": 0, "raw": "", "validation_errors": [f"Queue file not found: {path}"]}]
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError as exc:
            rejects.append({"line_number": line_number, "raw": line, "validation_errors": [f"Invalid JSON: {exc.msg}"]})
            continue
        if not isinstance(parsed, dict):
            rejects.append({"line_number": line_number, "raw": line, "validation_errors": ["JSONL row must be an object."]})
            continue
        rows.append(parsed)
    return rows, rejects


def validate_row(row: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for field in REQUIRED_FIELDS:
        if field not in row:
            errors.append(f"Missing required field: {field}")
    if "id" in row and not isinstance(row["id"], str):
        errors.append("Field id must be a string.")
    if "type" in row and row["type"] not in ALLOWED_TYPES:
        errors.append(f"Unsupported type: {row.get('type')}")
    if "status" in row and row["status"] not in ALLOWED_STATUSES:
        errors.append(f"Unsupported status: {row.get('status')}")
    if "payload" in row and not isinstance(row["payload"], dict):
        errors.append("Field payload must be an object.")
    if "provenance" in row and not isinstance(row["provenance"], dict):
        errors.append("Field provenance must be an object.")
    if "created_at" in row and not isinstance(row["created_at"], str):
        errors.append("Field created_at must be an ISO-8601 string.")
    if "validation_status" in row and row["validation_status"] not in VALIDATION_STATUSES:
        errors.append(f"Unsupported validation_status: {row.get('validation_status')}")
    return errors


def split_valid(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for row in rows:
        errors = validate_row(row)
        enriched = dict(row)
        enriched["validation_errors"] = errors
        enriched["validation_status"] = "FAIL" if errors else enriched.get("validation_status", "PASS")
        enriched["validated_at"] = utc_now()
        if errors:
            enriched["status"] = "rejected"
            rejected.append(enriched)
        else:
            if enriched["status"] == "queued":
                enriched["status"] = "accepted"
            accepted.append(enriched)
    return accepted, rejected


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def print_summary(*, accepted: int, rejected: int, parse_errors: int = 0) -> None:
    print(json.dumps({"accepted": accepted, "rejected": rejected, "parse_errors": parse_errors}, sort_keys=True))


def queue_arg_parser(description: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--input", default=str(QUEUE_PATH))
    parser.add_argument("--processed-output", default=str(PROCESSED_PATH))
    parser.add_argument("--rejected-output", default=str(REJECTED_PATH))
    return parser
