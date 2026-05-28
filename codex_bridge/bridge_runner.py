#!/usr/bin/env python3
import json
from pathlib import Path
from datetime import datetime, timezone
ROOT = Path(__file__).resolve().parent
QUEUE = ROOT / "requests.jsonl"
OUT = ROOT / "output"
STATUS = ROOT / "status.json"
OUT.mkdir(exist_ok=True)
def now():
    return datetime.now(timezone.utc).isoformat()
def load_requests():
    if not QUEUE.exists():
        return []
    rows = []
    for line in QUEUE.read_text().splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows
def write_requests(rows):
    QUEUE.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n")
def process(req):
    rid = req["id"]
    payload = req.get("payload", {})
    task = payload.get("task", "")
    md = f'''# Codex Bridge Output: {rid}
Generated: {now()}
## Task
{task}
## Execution Plan
1. Ingest source datasets.
2. Validate county/year coverage.
3. Normalize filings per 100,000 age-65+ residents.
4. Compute rolling-window baselines.
5. Add FHFA HPI exposure bins.
6. Flag outliers for human review.
7. Export reproducible tables and charts.
## Guardrails
- Treat statistical anomalies as leads, not proof.
- Preserve source URLs and retrieval dates.
- Separate observed counts, normalized rates, modeled expectations, and uncertainty.
'''
    json_plan = {
        "id": rid,
        "generated_at": now(),
        "task": task,
        "pipeline": [
            "fetch_csr",
            "extract_probate_conservatorship_filings",
            "fetch_ca_dof_e6_population",
            "fetch_fhfa_hpi",
            "normalize_rates",
            "rolling_window_baseline",
            "outlier_detection",
            "human_review_packet"
        ],
        "outputs": payload.get("outputs", [])
    }
    (OUT / f"{rid}_methodology.md").write_text(md)
    (OUT / f"{rid}_pipeline_plan.json").write_text(json.dumps(json_plan, indent=2))
def main():
    rows = load_requests()
    processed = []
    for req in rows:
        if req.get("status") != "queued":
            continue
        try:
            req["status"] = "processing"
            req["started_at"] = now()
            process(req)
            req["status"] = "done"
            req["finished_at"] = now()
        except Exception as e:
            req["status"] = "error"
            req["error"] = str(e)
        processed.append(req["id"])
    write_requests(rows)
    STATUS.write_text(json.dumps({
        "updated_at": now(),
        "processed": processed
    }, indent=2))
if __name__ == "__main__":
    main()
