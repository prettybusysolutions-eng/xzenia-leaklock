# TASK-REPORT-SYSTEM6-005

## Status
PASS

## Scope completed
Built System 6 Layer 5 for identity binding, evidence-backed outcomes, and verification scaffolding in `xzenia-saas`.

## What became more real
1. **Approval identity binding layer**
   - Decision, execution, and outcome flows now accept a structured actor contract:
     - `actor: { actor_id, actor_type, ... }`, or
     - top-level `actor_id` + `actor_type`
   - `models/db.py` now normalizes actor identity into structured payloads and stores:
     - `*_actor_id`
     - `*_actor_type`
     - `*_actor_payload`
     - `*_actor_is_legacy`
   - Existing loose string actors are still accepted only as a clearly marked compatibility path (`legacy_string_actor`).

2. **Outcome evidence requirement**
   - Outcome capture now requires at least one explicit evidence reference.
   - Evidence is stored as normalized JSON in:
     - `outcome_evidence`
     - `outcome_evidence_count`
   - Accepts explicit reference objects such as document URLs, note refs, attachment refs, or source record IDs.
   - No fake files or synthetic evidence generation was introduced.

3. **External verification hook scaffold**
   - Added execution and outcome verification scaffolding with status/path/notes fields:
     - `execution_verification_status`, `execution_verification_path`, `execution_verification_notes`, `execution_verified_at`
     - `outcome_verification_status`, `outcome_verification_path`, `outcome_verification_notes`, `outcome_verified_at`
   - Verification statuses are scaffold-only (`unverified`, `pending`, `verified`, `disputed`).
   - No fake verifier or simulated external confirmation was added.

4. **Operator-facing lifecycle truth surfacing**
   - Action inspection JSON now exposes structured actor, evidence, and verification fields.
   - Proof/report paths now surface:
     - evidenced outcomes
     - execution verification counts
     - outcome verification counts
     - action-level verification/evidence visibility in the HTML report
     - legacy actor visibility where compatibility mode was used

5. **Tests**
   - Added/updated tests for:
     - structured identity validation path
     - legacy actor backward-compat handling
     - outcome evidence requirement
     - verification scaffold propagation
     - report/UI route survival after Layer 5 changes

6. **Migration scaffold**
   - Added `migrations/005_system6_layer5_truth_contract.sql` to introduce the Layer 5 truth-contract columns and constraints.

## Verification
Executed:

```bash
pytest tests/test_system6.py tests/test_scanner.py -q
python3 -m py_compile models/db.py routes/api.py app.py
```

Result:
- `18 passed`
- Python compile check passed for touched modules

## Files changed
- `models/db.py`
- `routes/api.py`
- `tests/test_system6.py`
- `migrations/005_system6_layer5_truth_contract.sql`
- `TASK-REPORT-SYSTEM6-005.md`

## Exact remaining bottleneck
**Actor identity is now structurally bound, but still not cryptographically or session-auth bound to a real authenticated human principal at the API boundary.**

Layer 5 eliminated loose string-only truth as the default contract and made legacy paths explicit, but the surrounding app stack still needs real authentication/authorization enforcement and real external verifier integrations. Until that exists:
- a caller can still assert a structured actor payload without server-side identity proof
- verification status is a truthful scaffold, not an independent attestation engine
- evidence references are required, but the system does not yet dereference or validate those references against external source systems
