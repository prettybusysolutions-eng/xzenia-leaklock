# TASK-REPORT-SYSTEM6-004

## Status
PASS

## Scope completed
Built System 6 Layer 4 for the approval -> execution -> measured outcome loop in `xzenia-saas`.

### What became real
1. **Approval decision path**
   - Added API route: `POST /api/system6/actions/<action_id>/decision`
   - Added lifecycle validation in `models/db.py`
   - Requires explicit actor and only allows decisions on `pending` actions
   - Preserves human approval semantics with `decision_actor`, `decided_at`, `decision_notes`, and `approved_by` only when actually approved

2. **Execution status path**
   - Added API route: `POST /api/system6/actions/<action_id>/execution`
   - Only approved actions can move through execution states
   - Supports `pending`, `executed`, `failed`
   - Stores `execution_actor`, `execution_updated_at`, `execution_notes`, and `executed_at`

3. **Measured outcome capture path**
   - Added API route: `POST /api/system6/actions/<action_id>/outcome`
   - Only executed actions can receive measured outcomes
   - Stores `outcome_type`, `outcome_value`, `outcome_currency`, `outcome_notes`, `measured_at`
   - No auto-populated outcome values were introduced

4. **Deduplication guard**
   - `add_consequence_action()` now returns an existing open action for the same case if one already exists in `pending` or `approved`
   - Added partial unique index migration for one active action per case: `idx_consequence_actions_case_active`

5. **Operator-facing inspection path**
   - Added API route: `GET /api/system6/actions/<action_id>`
   - Added API route: `GET /api/system6/cases/<case_id>/actions`
   - Extended proof report with `recent_actions`
   - Extended `/ops/system6/proof/revenue-recovery` page with an **Action lifecycle** table

6. **Tests**
   - Approval route path
   - Execution route path
   - Outcome capture route path
   - Dedupe behavior for open actions
   - Existing System 6 proof/intake tests preserved and passing

## What is still simulated
- No real external remediation execution engine was added. Execution status is operator-recorded truth, not auto-verified operational telemetry.
- No cryptographic or external-system attestation was added for approvals, executions, or outcomes.
- Operator surface is minimal HTML/JSON inspection, not a full workflow UI.

## Verification
Executed:

```bash
pytest tests/test_system6.py tests/test_scanner.py -q
python3 -m py_compile models/db.py routes/api.py services/consequence.py app.py
```

Result:
- `14 passed`
- Python compile check passed for touched modules

## Files changed
- `models/db.py`
- `models/__init__.py`
- `routes/api.py`
- `tests/test_system6.py`
- `migrations/004_system6_layer4_lifecycle.sql`
- `TASK-REPORT-SYSTEM6-004.md`

## Exact unresolved weaknesses
1. **Approval identity trust is still string-based**
   - `actor` is recorded as provided; there is no authenticated human identity binding in this layer.

2. **Execution truth is still operator-asserted**
   - Layer 4 records truthful state transitions, but it does not independently verify that an external intervention actually occurred.

3. **Outcome truth is still manually entered**
   - Layer 4 prevents fabricated auto-population, but it does not require documentary evidence before storing outcome values.

4. **Partial unique index assumes clean existing data**
   - If a deployed database already contains multiple open actions for the same case, the unique index may need data cleanup before migration succeeds.

5. **API mutation endpoints are not yet auth-gated here**
   - Routes enforce lifecycle semantics, not operator authentication/authorization. Security enforcement must be handled by the surrounding app stack.
