#!/usr/bin/env python3
from __future__ import annotations

import json


def main() -> None:
    print(json.dumps({
        "status": "dry_run",
        "message": "Bridge repo does not regenerate GIS evidence directly. Run this command in housing-fraud-intel-api.",
        "evidence_boundary": "No outputs/gis_model files were modified by this Bridge dry run."
    }, sort_keys=True))


if __name__ == "__main__":
    main()

