# System 6 Taskboard

**Objective:** Create one undeniable production consequence loop in revenue recovery.

## Phase A — Data Truth
- [x] Create consequence tables
- [x] Add helper functions for case/action/outcome lifecycle
- [x] Exclude synthetic/demo events from proof metrics
- [ ] Define canonical evidence JSON schema for revenue recovery cases
- [ ] Backfill `is_synthetic=TRUE` for all demo/sample-derived records

## Phase B — Live Intake
- [ ] Select one real external source of billing truth
- [ ] Create ingestion path from source event to `saas_consequence_cases`
- [ ] Ensure every ingested case has stable `source_event_id`
- [ ] Attach raw evidence snapshots

## Phase C — Recommendation Layer
- [ ] Convert leak detections into governed recommendations
- [ ] Record causal hypothesis for each recommendation
- [ ] Route all proposed actions through approval gate

## Phase D — Execution + Outcome
- [ ] Record approval / rejection decisions
- [ ] Record execution status
- [ ] Record measurable outcome (`recovered_revenue`, `retained_revenue`, `avoided_loss`, `no_effect`)
- [ ] Build proof-metric query and operator report

## Phase E — Proof Threshold
- [ ] 10 real cases ingested
- [ ] 3 governed actions proposed
- [ ] 1 measurable real gain or avoided loss
- [ ] Full evidence chain complete for all proof cases

## External Attestation Milestone
- [x] One real GitHub-native attestation loop completed
  - repo: `prettybusysolutions-eng/xzenia-attestation`
  - issue: `#1`
  - PR: `#2`
  - merge commit: `48b65c26cb6326b6b2fdd3442eb6c8ffe82488a5`
- [ ] Promote from GitHub-native proof to business-domain proof
- [ ] Bind authenticated principal at the app/API boundary
- [ ] Dereference and validate outcome evidence against source systems

## Non-goals
- [ ] No simulated ROI counted as proof
- [ ] No seeded/demo rows in proof metrics
- [ ] No claim of completion before measurable external consequence exists
