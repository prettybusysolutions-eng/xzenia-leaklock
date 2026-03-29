# System 6 — Consequence Engine Scaffold

**Status:** Scaffold built
**Date:** 2026-03-29
**Doctrine:** Build from truth, not performance.

## What this scaffold adds

System 6 now has a concrete persistence layer inside LeakLock / xzenia-saas:

- `saas_consequence_cases`
- `saas_consequence_actions`
- DB bootstrap wiring in `app.py`
- helper functions in `models/db.py`
- SQL migration in `migrations/003_system6_consequence_engine.sql`

## Purpose

This scaffold makes it possible to track a real consequence loop from:

1. source event
2. anomaly detection
3. recommendation
4. approval / rejection
5. execution
6. measured outcome

It also introduces a hard anti-fake boundary:
- `is_synthetic = TRUE` records are excluded from proof metrics

## Tables

### `saas_consequence_cases`
Represents a real or synthetic case under investigation.

Fields include:
- `domain`
- `source_system`
- `source_event_id`
- `scan_id`
- `customer_ref`
- `anomaly_type`
- `evidence` (JSONB)
- `is_synthetic`
- `status`
- `detected_at`

### `saas_consequence_actions`
Represents a recommendation and its decision/execution/outcome lifecycle.

Fields include:
- `recommendation`
- `causal_hypothesis`
- `requires_approval`
- `approval_status`
- `approved_by`
- `execution_status`
- `outcome_type`
- `outcome_value`
- `outcome_currency`
- `outcome_notes`

## Available helpers

From `models.db`:
- `create_consequence_case(...)`
- `add_consequence_action(...)`
- `record_action_decision(...)`
- `record_action_execution(...)`
- `record_action_outcome(...)`
- `get_proof_metrics(domain='revenue_recovery')`

## What this does NOT claim yet

This does **not** mean System 6 is complete.

The scaffold only provides the data model and bootstrap hooks.
System 6 is complete only when real external cases, approved actions, and measured outcomes exist.

## Definition of done still outstanding

System 6 is only complete when:
- one live domain is connected to a real external source
- at least 10 real external cases are ingested
- at least 3 governed actions are proposed
- at least 1 approved action produces measurable external gain or avoided loss
- all proof metrics exclude synthetic/demo events
