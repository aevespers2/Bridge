# Epistemic Firewall

Bridge separates proposal from evidence.

```text
Human observations
        ↓
Claims / hypotheses
        ↓
Request queue
        ↓
Validation layer
        ↓
Evidence graph
        ↓
Published state
```

## Layer 1: Observations

Raw observations have no conclusion attached.

```json
{
  "source": "court_record",
  "observed_at": "2011-04-17",
  "observation": "case transferred"
}
```

## Layer 2: Claims

Claims are assertions or hypotheses. They are not evidence.

```json
{
  "claim": "Transfer appears unusual.",
  "status": "hypothesis"
}
```

## Layer 3: Validation

Validation records use only:

```text
PASS
FAIL
UNKNOWN
```

`UNKNOWN` is a first-class result. It means the claim is not reproducible or source-tested yet.

## Layer 4: Evidence Graph

The graph links:

```text
document -> observation
observation -> claim
validation -> target
source -> supporting evidence
source -> contradicting evidence
```

It preserves uncertainty instead of collapsing records into conclusions.

## Layer 5: Published State

Published state is compiled output. ChatGPT proposals cannot directly mutate it.

```text
Request Queue = source/proposals
Evidence Gist = read-only published state
Codex = validator and publisher
```

