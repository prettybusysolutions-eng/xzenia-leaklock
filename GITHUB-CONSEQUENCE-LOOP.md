# GitHub-First Consequence Loop

**Purpose:** give Xzenia a real externally attested consequence domain before private business identifiers are available.

## Why GitHub first
GitHub provides all four things the current system lacks:
1. stable external IDs
2. authenticated user identities
3. externally visible state transitions
4. verifiable outcomes (issues, PRs, reviews, workflow runs)

## What counts as a case
A GitHub case is any externally addressable object that needs governed intervention:
- an open issue that requires triage or remediation
- an open pull request that requires review/merge decision
- a failed workflow run that requires retry or fix

## What counts as approval
- a GitHub review decision
- or a human-authenticated decision inside Xzenia tied to a real principal

## What counts as execution
- a PR merge
- a workflow rerun
- a comment or state change initiated under governance

## What counts as verification
- GitHub API / gh CLI confirms the state transition actually occurred
- workflow/run/pr/issue IDs match the recorded evidence

## What counts as outcome
- issue closed
- PR merged
- workflow passes after intervention
- linked issue resolved by merged change

## Scaffold built
- `domains/github_ops_domain.py`
- `services/github_consequence.py`
- `scripts/github_consequence_preflight.py`

## Current preflight state
The scaffold can report:
- whether `gh` is installed
- whether `gh` is authenticated
- whether a git remote exists
- what repo slug is inferred

## Remaining external dependency
To run the live loop, one of these must become true:
- `gh auth login` completes on this machine
- or a valid GitHub token/app credential is configured under Kamm-controlled governance

## The shortest path now
1. authenticate `gh`
2. choose one target repo
3. ingest one issue / PR / workflow run as a consequence case
4. run it through the full approval → execution → verification → outcome chain
5. preserve misses as first-class evidence
