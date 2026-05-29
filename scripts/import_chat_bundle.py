#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from chat_bundle import import_bundle


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate and dispatch a Chat Bundle into the Bridge queue.")
    parser.add_argument("bundle", help="Path to bundle JSON.")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    status = import_bundle(Path(args.bundle), dry_run=args.dry_run)
    print(json.dumps(status, sort_keys=True))
    if status["validation_errors"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
