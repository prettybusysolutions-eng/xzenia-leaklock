# System 5 v2 - Operational Reliability Proof

**Date:** June 10, 2026
**Verdict:** PASS, with the v1 limitation corrected

## Why v2 Was Required

System 5 v1 correctly proved that two domains could satisfy one structural
declaration contract. It did not prove activation portability:

- anomaly rules could remain deferred
- evidence requirements were not modeled
- causal mappings were not required
- action risk and verification policy were not enforced
- no generic evidence-to-action proposal path existed

The v1 domains remain valid and unchanged. System 5 v2 adds a generic
activation layer around them instead of moving operational-reliability logic
into the substrate.

## Generic Substrate Added

- `cognitive/domain_activation.py`
  - ontology contract
  - evidence requirements
  - causal mappings
  - action risk and approval policy
  - verification requirements
  - read-only activation health check
  - schema-checked signal evaluation
  - proposal generation without action execution
- `cognitive/prove_domain_pack.py`
  - loads any v2 pack
  - validates activation
  - evaluates evidence cases
  - writes a machine-readable proof report

## Third Domain

`domains/operational_reliability_domain.py` defines:

- component reachability
- workflow execution
- disk capacity
- incident ontology
- evidence requirements
- causal hypotheses
- bounded diagnostics
- approval-gated code repair and disk cleanup

The generic validator and evaluator contain no GitHub, OpenClaw, macOS, or disk
cleanup branching.

## Real Evidence Cases

1. `platform-spine` workflow run `27299464728`
   - observed conclusion: `failure`
   - detected rule: `workflow_execution_failed`
   - low-risk diagnostics: ready for governed execution
   - code repair: waiting for human approval

2. Host disk pressure before cleanup
   - observed utilization: 97 percent
   - free space: 3.7 GiB
   - detected rule: `disk_capacity_critical`
   - evidence preservation: ready for governed execution
   - residue removal: critical risk, waiting for human approval

No action was executed by the proof runtime.

## Verification

- Original revenue-recovery v1 domain: pass
- Original pretty-busy-cleaning v1 domain: pass
- Operational-reliability v1 declaration: 0 violations, 0 warnings
- Operational-reliability v2 activation pack: pass
- Real evidence cases accepted: 2 of 2
- Causal findings produced: 2
- Actions executed by proof runtime: 0
- New adversarial tests: 7 passed
- Full repository suite: 25 passed

Evidence:

- `evidence/system5-v2/operational-reliability-cases.json`
- `evidence/system5-v2/operational-reliability-proof.json`

## Hard Verdict

The old contract was domain-portable but activation-incomplete. The new generic
activation layer was one required substrate correction.

After that correction, operational reliability onboarded as a third,
structurally different domain without domain-specific changes to the validator
or evaluator. Missing evidence blocks all proposed actions, and critical
actions cannot be declared without human approval.

This proves generalized onboarding and governed diagnostic proposal behavior.
It does not prove external value, autonomous execution, or System 9 domain
replication. Those require real consequence under later system gates.
