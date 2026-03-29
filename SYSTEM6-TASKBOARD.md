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

## Non-goals
- [ ] No simulated ROI counted as proof
- [ ] No seeded/demo rows in proof metrics
- [ ] No claim of completion before measurable external consequence exists
