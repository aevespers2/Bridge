from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PENDING_DIR = ROOT / "bundles" / "pending"
PROCESSED_DIR = ROOT / "bundles" / "processed"
REJECTED_DIR = ROOT / "bundles" / "rejected"
QUEUE_PATH = ROOT / "queues" / "chatgpt_codex_work_queue.jsonl"
STATUS_PATH = ROOT / "reports" / "chat_bundle_status.json"

SAFETY_BOUNDARIES = [
    "Do not ingest raw unfiltered chat as evidence.",
    "Do not treat chat claims as facts.",
    "Do not modify evidence outputs directly.",
    "Distinguish observed, inferred, unverified, and requested items.",
]

REQUEST_TYPES = {
    "codex_task",
    "add_apn",
    "review_apn",
    "link_apns",
    "add_note",
    "request_office_pull",
    "refresh_snapshots",
    "publish_gist",
    "run_tests",
    "mark_resolved",
}
PRIORITIES = {"low", "medium", "high", "critical", "urgent"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def stable_id(prefix: str, text: str) -> str:
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return f"{prefix}-{stamp}-{digest}"


def read_json(path: Path) -> dict[str, Any]:
    parsed = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(parsed, dict):
        raise ValueError("JSON document must be an object.")
    return parsed


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def append_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def source_digest(path: Path | None) -> str:
    if path is None or not path.exists():
        return ""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def create_bundle(
    *,
    purpose: str,
    conversation_summary: str,
    codex_instructions: str,
    input_path: Path | None = None,
    key_decisions: list[str] | None = None,
    open_questions: list[str] | None = None,
    tasks_requested: list[Any] | None = None,
    evidence_links: list[str] | None = None,
    bridge_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    bundle_seed = "\n".join([purpose, conversation_summary, codex_instructions, source_digest(input_path)])
    return {
        "bundle_id": stable_id("chatbundle", bundle_seed),
        "created_by": "chatgpt",
        "created_at": utc_now(),
        "purpose": purpose,
        "conversation_summary": conversation_summary,
        "key_decisions": key_decisions or [],
        "open_questions": open_questions or [],
        "tasks_requested": tasks_requested or [],
        "evidence_links": evidence_links or [],
        "bridge_context": bridge_context or {},
        "safety_boundaries": SAFETY_BOUNDARIES,
        "codex_instructions": codex_instructions,
        "source_digest": source_digest(input_path),
        "validation_errors": [],
    }


def validate_bundle(bundle: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = [
        "bundle_id",
        "created_by",
        "created_at",
        "purpose",
        "conversation_summary",
        "tasks_requested",
        "safety_boundaries",
        "codex_instructions",
    ]
    for field in required:
        if field not in bundle:
            errors.append(f"Missing required field: {field}")
    if bundle.get("created_by") not in {"chatgpt", "user", "codex"}:
        errors.append("created_by must be chatgpt, user, or codex.")
    for field in ["purpose", "conversation_summary", "codex_instructions"]:
        if field in bundle and not isinstance(bundle[field], str):
            errors.append(f"{field} must be a string.")
        elif field in bundle and len(bundle[field].strip()) < 3:
            errors.append(f"{field} must contain at least 3 characters.")
    if not isinstance(bundle.get("tasks_requested", []), list):
        errors.append("tasks_requested must be an array.")
    if not isinstance(bundle.get("safety_boundaries", []), list) or not bundle.get("safety_boundaries"):
        errors.append("safety_boundaries must be a non-empty array.")
    for index, task in enumerate(bundle.get("tasks_requested", [])):
        if isinstance(task, str):
            if len(task.strip()) < 3:
                errors.append(f"tasks_requested[{index}] must not be blank.")
            continue
        if not isinstance(task, dict):
            errors.append(f"tasks_requested[{index}] must be a string or object.")
            continue
        if not str(task.get("title", "")).strip():
            errors.append(f"tasks_requested[{index}].title is required.")
        if task.get("request_type", "codex_task") not in REQUEST_TYPES:
            errors.append(f"tasks_requested[{index}].request_type is unsupported.")
        if task.get("priority", "medium") not in PRIORITIES:
            errors.append(f"tasks_requested[{index}].priority is unsupported.")
    return errors


def bundle_to_requests(bundle: dict[str, Any]) -> list[dict[str, Any]]:
    requests: list[dict[str, Any]] = []
    for index, task in enumerate(bundle.get("tasks_requested", []), start=1):
        if isinstance(task, str):
            title = task
            instructions = bundle["codex_instructions"]
            request_type = "codex_task"
            priority = "medium"
            acceptance_criteria: list[str] = []
            commands: list[str] = []
        else:
            title = str(task.get("title"))
            instructions = str(task.get("instructions") or bundle["codex_instructions"])
            request_type = str(task.get("request_type", "codex_task"))
            priority = str(task.get("priority", "medium"))
            acceptance_criteria = list(task.get("acceptance_criteria", []))
            commands = list(task.get("commands", []))
        requests.append(
            {
                "request_id": f"{bundle['bundle_id']}-{index:03d}",
                "request_type": request_type,
                "source": "chatgpt",
                "title": title,
                "instructions": instructions,
                "target_repo": "aevespers2/Bridge",
                "priority": priority,
                "status": "pending",
                "acceptance_criteria": acceptance_criteria,
                "commands": commands,
                "evidence_links": list(bundle.get("evidence_links", [])),
                "human_signal": f"From chat bundle {bundle['bundle_id']}: {bundle['purpose']}",
                "system_signal": "Structured chat bundle dispatch; raw chat remains outside the evidence layer.",
                "shared_priority": bundle.get("purpose", ""),
                "shipping_goal": title,
                "evidence_boundary": "Chat bundle content is task context, not proof or evidence.",
            }
        )
    return requests


def import_bundle(bundle_path: Path, *, dry_run: bool = False) -> dict[str, Any]:
    bundle = read_json(bundle_path)
    errors = validate_bundle(bundle)
    bundle["validation_errors"] = errors
    requests = [] if errors else bundle_to_requests(bundle)
    destination = REJECTED_DIR / bundle_path.name if errors else PROCESSED_DIR / bundle_path.name
    status = {
        "schema": "chat_bundle_status.v1",
        "generated_at": utc_now(),
        "bundle_id": bundle.get("bundle_id", ""),
        "bundle_path": str(bundle_path),
        "status": "rejected" if errors else "processed",
        "validation_errors": errors,
        "requests_generated": len(requests),
        "queue_output": str(QUEUE_PATH),
        "evidence_boundary": "Bundle import stages validated task requests only; it does not modify evidence outputs.",
        "dry_run": dry_run,
    }
    if not dry_run:
        write_json(destination, bundle)
        append_jsonl(QUEUE_PATH, requests)
        write_json(STATUS_PATH, status)
    return status
