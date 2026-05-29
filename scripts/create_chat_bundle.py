#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from chat_bundle import PENDING_DIR, create_bundle, write_json


def parse_json_array(value: str) -> list[str]:
    if not value:
        return []
    parsed = json.loads(value)
    if not isinstance(parsed, list) or not all(isinstance(item, str) for item in parsed):
        raise argparse.ArgumentTypeError("value must be a JSON array of strings")
    return parsed


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a structured Chat Bundle without ingesting raw chat as evidence.")
    parser.add_argument("--input", help="Optional local notes file used only for digest/provenance.")
    parser.add_argument("--purpose", required=True)
    parser.add_argument("--conversation-summary", required=True)
    parser.add_argument("--codex-instructions", required=True)
    parser.add_argument("--task", action="append", default=[], help="Task title. May be repeated.")
    parser.add_argument("--key-decisions", type=parse_json_array, default=[])
    parser.add_argument("--open-questions", type=parse_json_array, default=[])
    parser.add_argument("--evidence-links", type=parse_json_array, default=[])
    parser.add_argument("--bridge-context-json", default="{}")
    parser.add_argument("--output")
    args = parser.parse_args()

    input_path = Path(args.input) if args.input else None
    bridge_context = json.loads(args.bridge_context_json)
    if not isinstance(bridge_context, dict):
        raise SystemExit("--bridge-context-json must be a JSON object")
    bundle = create_bundle(
        purpose=args.purpose,
        conversation_summary=args.conversation_summary,
        codex_instructions=args.codex_instructions,
        input_path=input_path,
        key_decisions=args.key_decisions,
        open_questions=args.open_questions,
        tasks_requested=args.task,
        evidence_links=args.evidence_links,
        bridge_context=bridge_context,
    )
    output = Path(args.output) if args.output else PENDING_DIR / f"{bundle['bundle_id']}.json"
    write_json(output, bundle)
    print(json.dumps({"bundle_id": bundle["bundle_id"], "output": str(output)}, sort_keys=True))


if __name__ == "__main__":
    main()
