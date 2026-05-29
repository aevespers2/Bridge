#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

from bridge_queue import print_summary, queue_arg_parser, read_jsonl, split_valid, write_jsonl


def main() -> None:
    parser = queue_arg_parser("Validate and process the ChatGPT Bridge request queue.")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
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

