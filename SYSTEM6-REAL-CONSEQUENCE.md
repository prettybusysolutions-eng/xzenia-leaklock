# System 6 Real Consequence Proof

System 6 now has a machine-verifiable operational consequence proof built from
real GitHub workflow events.

## Proof set

- 10 externally addressable failed workflow runs
- 4 governed intervention proposals
- 4 human-approved, executed interventions
- 4 later successful workflow outcomes
- GitHub API dereferencing for every source and outcome snapshot

The evidence bundle is:

`evidence/system6/github-ops-2026-06-10.json`

Run the proof locally:

```bash
python3 scripts/system6_github_proof.py \
  --input evidence/system6/github-ops-2026-06-10.json \
  --output evidence/system6/github-ops-2026-06-10-report.json \
  --verify-live
```

## Truth boundary

This proves that Xzenia can bind real external events to governed proposals,
human approvals, executed changes, and externally verified operational
outcomes.

It does not prove revenue recovery, customer value, or monetary avoided loss.
Those claims remain blocked until a production billing source and a measured
business outcome are available.
