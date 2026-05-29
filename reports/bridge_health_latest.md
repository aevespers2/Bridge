# Bridge Health Dashboard

Generated: `2026-05-29T08:53:43.360753+00:00`

Overall status: `ok`

## Queue Counts

- Work queue: `22`
- Processed: `22`
- Rejected: `0`
- Blocked: `0`
- Local processed: `1`
- Local rejected: `0`

## Latest Routine Check

- Start: `2026-05-29T06:04:59.043485+00:00`
- End: `2026-05-29T06:05:03.101061+00:00`
- Exit: `success`
- Counts: `{"commands": 9, "failed": 0, "succeeded": 9}`

## Gist Snapshot

- Latest timestamp: `unknown`
- Status: `timestamp_unknown`

- summary: https://gist.githubusercontent.com/GeorgeTownSabatical/ea83e2a96538900b5a0c0ca0b58b76b4/raw/local_summary.json
- seed_apn_40128307: https://gist.githubusercontent.com/GeorgeTownSabatical/ea83e2a96538900b5a0c0ca0b58b76b4/raw/local_40128307.json
- ranked25: https://gist.githubusercontent.com/GeorgeTownSabatical/ea83e2a96538900b5a0c0ca0b58b76b4/raw/local_ranked25.json
- pull_list100: https://gist.githubusercontent.com/GeorgeTownSabatical/ea83e2a96538900b5a0c0ca0b58b76b4/raw/local_pull_list100.json

## Tests

- Status: `pass`
- Source: `latest_bridge_run.command_results`
- Command: `python -m pytest`

## Scheduler

`external/manual; Bridge repo does not install launchd`

## Command Results

- Results: `22`
- Executed: `22`
- Failed: `0`
- Rejected: `0`

## Top Active Tasks

- `critical` `pending`: Add 15-minute routine Bridge check workflow
- `critical` `pending`: Add evidence ledger and provenance spine
- `critical` `pending`: Add idempotent Bridge task ledger and deduplication
- `critical` `pending`: Add parcel lineage graph export
- `critical` `pending`: Build assessor-office packet generator
- `critical` `pending`: Build first record-retrieval playbook
- `critical` `pending`: Build safe Bridge command service for routine Codex checks
- `critical` `pending`: Design QSOF-integrated service bridge architecture

## Boundary

Health dashboard is operational status only; it does not prove or alter evidence claims.
