#!/usr/bin/env bash
set -euo pipefail

cat <<'JSON'
{"status":"dry_run","message":"Bridge publish script is intentionally inert. Public evidence Gist publishing must be explicitly configured and run from the validated GIS pipeline.","evidence_boundary":"No Gist was modified."}
JSON

