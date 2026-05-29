#!/usr/bin/env python3
from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
WORK_QUEUE_PATH = ROOT / "queues" / "chatgpt_codex_work_queue.jsonl"
PROCESSED_QUEUE_PATH = ROOT / "queues" / "chatgpt_codex_processed.jsonl"
REJECTED_QUEUE_PATH = ROOT / "queues" / "chatgpt_codex_rejected.jsonl"
LOCAL_PROCESSED_PATH = ROOT / "exports" / "chatgpt_request_queue_processed.jsonl"
LOCAL_REJECTED_PATH = ROOT / "exports" / "chatgpt_request_queue_rejected.jsonl"
LATEST_RUN_PATH = ROOT / "reports" / "latest_bridge_run.json"
ROUTINE_CHECK_PATH = ROOT / "reports" / "routine_bridge_check_latest.json"
REPRO_REPORT_PATH = ROOT / "reports" / "reproducibility_report.json"
TASK_LEDGER_PATH = ROOT / "reports" / "bridge_task_ledger.jsonl"
COMMAND_RESULTS_PATH = ROOT / "reports" / "bridge_command_results.jsonl"
JSON_OUTPUT = ROOT / "reports" / "bridge_health_latest.json"
MD_OUTPUT = ROOT / "reports" / "bridge_health_latest.md"

GIST_URLS = {
    "summary": "https://gist.githubusercontent.com/GeorgeTownSabatical/ea83e2a96538900b5a0c0ca0b58b76b4/raw/local_summary.json",
    "seed_apn_40128307": "https://gist.githubusercontent.com/GeorgeTownSabatical/ea83e2a96538900b5a0c0ca0b58b76b4/raw/local_40128307.json",
    "ranked25": "https://gist.githubusercontent.com/GeorgeTownSabatical/ea83e2a96538900b5a0c0ca0b58b76b4/raw/local_ranked25.json",
    "pull_list100": "https://gist.githubusercontent.com/GeorgeTownSabatical/ea83e2a96538900b5a0c0ca0b58b76b4/raw/local_pull_list100.json",
}


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


def title_for(row: dict[str, Any]) -> str:
    return str(row.get("title") or row.get("bridge_title") or row.get("payload", {}).get("title") or row.get("id") or "untitled")


def priority_for(row: dict[str, Any]) -> str:
    return str(row.get("priority") or row.get("payload", {}).get("priority") or "unknown")


def status_for(row: dict[str, Any]) -> str:
    return str(row.get("status") or row.get("request_status") or row.get("bridge_status") or "unknown")


def count_status(rows: list[dict[str, Any]]) -> dict[str, int]:
    return dict(sorted(Counter(status_for(row) for row in rows).items()))


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def top_active_tasks(work_rows: list[dict[str, Any]], processed_rows: list[dict[str, Any]], limit: int = 8) -> list[dict[str, str]]:
    processed_titles = {title_for(row) for row in processed_rows}
    priority_rank = {"critical": 0, "high": 1, "medium": 2, "low": 3, "unknown": 4}
    candidates = [
        row
        for row in work_rows
        if status_for(row) in {"pending", "queued", "processing", "accepted"} and title_for(row) not in processed_titles
    ]
    if not candidates:
        candidates = [row for row in work_rows if status_for(row) in {"pending", "queued", "processing", "accepted"}]
    candidates.sort(key=lambda row: (priority_rank.get(priority_for(row), 4), title_for(row)))
    return [
        {
            "title": title_for(row),
            "priority": priority_for(row),
            "status": status_for(row),
            "request_type": str(row.get("request_type") or row.get("type") or "unknown"),
        }
        for row in candidates[:limit]
    ]


def latest_command_summary(command_rows: list[dict[str, Any]], latest_run: dict[str, Any]) -> dict[str, Any]:
    from_run = latest_run.get("command_results")
    if isinstance(from_run, dict):
        return from_run
    statuses = Counter(str(row.get("status", "unknown")) for row in command_rows)
    failed = sum(1 for row in command_rows if int(row.get("exit_code") or 0) != 0)
    return {
        "command_result_count": len(command_rows),
        "executed_count": statuses.get("executed", 0),
        "failed_count": failed,
        "rejected_count": statuses.get("rejected", 0),
        "latest_results": command_rows[-10:],
    }


def infer_test_status(latest_run: dict[str, Any], repro_report: dict[str, Any], command_summary: dict[str, Any]) -> dict[str, Any]:
    latest_results = command_summary.get("latest_results", [])
    test_results = [
        row
        for row in latest_results
        if isinstance(row, dict) and ("pytest" in str(row.get("command", "")) or "unittest" in str(row.get("command", "")))
    ]
    if test_results:
        latest = test_results[-1]
        return {
            "status": "pass" if int(latest.get("exit_code") or 0) == 0 else "fail",
            "source": "latest_bridge_run.command_results",
            "command": latest.get("command"),
            "completed_at": latest.get("completed_at"),
        }
    if repro_report:
        return {
            "status": "pass" if repro_report.get("reproducible") else "unknown",
            "source": "reports/reproducibility_report.json",
            "command": "python -m unittest discover -s tests",
            "completed_at": repro_report.get("generated_at"),
        }
    if latest_run:
        return {"status": "unknown", "source": "reports/latest_bridge_run.json"}
    return {"status": "unknown", "source": "no local test report"}


def build_health() -> dict[str, Any]:
    work_rows = read_jsonl(WORK_QUEUE_PATH)
    processed_rows = read_jsonl(PROCESSED_QUEUE_PATH)
    rejected_rows = read_jsonl(REJECTED_QUEUE_PATH)
    local_processed_rows = read_jsonl(LOCAL_PROCESSED_PATH)
    local_rejected_rows = read_jsonl(LOCAL_REJECTED_PATH)
    task_ledger_rows = read_jsonl(TASK_LEDGER_PATH)
    command_rows = read_jsonl(COMMAND_RESULTS_PATH)
    latest_run = read_json(LATEST_RUN_PATH)
    routine_check = read_json(ROUTINE_CHECK_PATH)
    repro_report = read_json(REPRO_REPORT_PATH)
    command_summary = latest_command_summary(command_rows, latest_run)
    latest_routine = latest_run.get("routine_check") if isinstance(latest_run.get("routine_check"), dict) else routine_check

    queue_counts = {
        "work_queue": len(work_rows),
        "processed": len(processed_rows),
        "rejected": len(rejected_rows),
        "local_processed": len(local_processed_rows),
        "local_rejected": len(local_rejected_rows),
        "blocked": int(latest_run.get("blocked_count") or 0),
        "work_queue_by_status": count_status(work_rows),
        "processed_by_status": count_status(processed_rows),
    }
    latest_gist_timestamp = (
        latest_run.get("latest_gist_timestamp")
        or latest_run.get("snapshot_timestamp_utc")
        or latest_run.get("gist_snapshot_timestamp")
        or "unknown"
    )
    return {
        "schema": "bridge_health_dashboard.v1",
        "generated_at": utc_now(),
        "repo": "aevespers2/Bridge",
        "overall_status": "degraded" if rejected_rows or local_rejected_rows else "ok",
        "queue_counts": queue_counts,
        "latest_routine_check": {
            "start_time": latest_routine.get("start_time"),
            "end_time": latest_routine.get("end_time"),
            "exit_status": latest_routine.get("exit_status"),
            "counts": latest_routine.get("counts"),
        },
        "gist": {
            "latest_snapshot_timestamp": latest_gist_timestamp,
            "status": "timestamp_unknown" if latest_gist_timestamp == "unknown" else "timestamp_reported",
            "urls": GIST_URLS,
        },
        "test_status": infer_test_status(latest_run, repro_report, command_summary),
        "scheduler_mode": latest_run.get("scheduler_mode") or "external/manual; Bridge repo does not install launchd",
        "ledger_status": {
            "task_ledger_entries": len(task_ledger_rows),
            "latest_run_task_ledger": latest_run.get("task_ledger"),
        },
        "command_results": {
            "command_result_count": command_summary.get("command_result_count", len(command_rows)),
            "executed_count": command_summary.get("executed_count", 0),
            "failed_count": command_summary.get("failed_count", 0),
            "rejected_count": command_summary.get("rejected_count", 0),
        },
        "top_active_tasks": top_active_tasks(work_rows, processed_rows),
        "reports": {
            "latest_bridge_run": display_path(LATEST_RUN_PATH),
            "routine_check_latest": display_path(ROUTINE_CHECK_PATH),
            "reproducibility_report": display_path(REPRO_REPORT_PATH),
            "health_json": display_path(JSON_OUTPUT),
            "health_markdown": display_path(MD_OUTPUT),
        },
        "evidence_boundary": "Health dashboard is operational status only; it does not prove or alter evidence claims.",
    }


def markdown(health: dict[str, Any]) -> str:
    queue = health["queue_counts"]
    routine = health["latest_routine_check"]
    commands = health["command_results"]
    top_tasks = "\n".join(
        f"- `{task['priority']}` `{task['status']}`: {task['title']}" for task in health["top_active_tasks"]
    ) or "- none"
    gist_urls = "\n".join(f"- {name}: {url}" for name, url in health["gist"]["urls"].items())
    return f"""# Bridge Health Dashboard

Generated: `{health['generated_at']}`

Overall status: `{health['overall_status']}`

## Queue Counts

- Work queue: `{queue['work_queue']}`
- Processed: `{queue['processed']}`
- Rejected: `{queue['rejected']}`
- Blocked: `{queue['blocked']}`
- Local processed: `{queue['local_processed']}`
- Local rejected: `{queue['local_rejected']}`

## Latest Routine Check

- Start: `{routine.get('start_time') or 'unknown'}`
- End: `{routine.get('end_time') or 'unknown'}`
- Exit: `{routine.get('exit_status') or 'unknown'}`
- Counts: `{json.dumps(routine.get('counts'), sort_keys=True)}`

## Gist Snapshot

- Latest timestamp: `{health['gist']['latest_snapshot_timestamp']}`
- Status: `{health['gist']['status']}`

{gist_urls}

## Tests

- Status: `{health['test_status']['status']}`
- Source: `{health['test_status']['source']}`
- Command: `{health['test_status'].get('command') or 'unknown'}`

## Scheduler

`{health['scheduler_mode']}`

## Command Results

- Results: `{commands['command_result_count']}`
- Executed: `{commands['executed_count']}`
- Failed: `{commands['failed_count']}`
- Rejected: `{commands['rejected_count']}`

## Top Active Tasks

{top_tasks}

## Boundary

{health['evidence_boundary']}
"""


def main() -> None:
    health = build_health()
    JSON_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    JSON_OUTPUT.write_text(json.dumps(health, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    MD_OUTPUT.write_text(markdown(health), encoding="utf-8")
    print(json.dumps({"json": str(JSON_OUTPUT), "markdown": str(MD_OUTPUT), "status": health["overall_status"]}, sort_keys=True))


if __name__ == "__main__":
    main()
