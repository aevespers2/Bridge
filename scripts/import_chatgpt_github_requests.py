#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from bridge_queue import print_summary, read_jsonl, split_valid, write_jsonl


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import ChatGPT/GitHub requests into the Bridge queue.")
    parser.add_argument("--source", choices=["local", "issue"], default="local")
    parser.add_argument("--input", default="exports/chatgpt_request_queue.jsonl")
    parser.add_argument("--processed-output", default="exports/chatgpt_request_queue_processed.jsonl")
    parser.add_argument("--rejected-output", default="exports/chatgpt_request_queue_rejected.jsonl")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.source != "local":
        print(f"source={args.source} is reserved for future GitHub Issue import; use --source local for this dry-run bridge.", file=sys.stderr)
        raise SystemExit(2)
    rows, parse_rejects = read_jsonl(Path(args.input))
    accepted, rejected = split_valid(rows)
    rejected = parse_rejects + rejected
    if not args.dry_run:
        write_jsonl(Path(args.processed_output), accepted)
        write_jsonl(Path(args.rejected_output), rejected)
    print_summary(accepted=len(accepted), rejected=len(rejected), parse_errors=len(parse_rejects))
    if rejected:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

