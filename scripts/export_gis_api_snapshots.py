#!/usr/bin/env python3
from __future__ import annotations

import json


def main() -> None:
    print(json.dumps({
        "status": "dry_run",
        "message": "Bridge repo does not export evidence snapshots directly. Use the main GIS repo exporter after validation.",
        "evidence_boundary": "No public evidence Gist or GIS snapshot was modified."
    }, sort_keys=True))


if __name__ == "__main__":
    main()

