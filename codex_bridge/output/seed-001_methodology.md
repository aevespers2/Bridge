# Codex Bridge Output: seed-001
Generated: 2026-05-28T05:14:44.929714+00:00
## Task
Build normalized California probate/conservatorship filing analysis using CSR, E-6 age 65+ denominators, and FHFA HPI exposures.
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
