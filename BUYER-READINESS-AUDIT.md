# LeakLock Buyer-Readiness Audit

Audit date: 2026-06-13

## Verdict

LeakLock is a functioning revenue-leak analysis prototype with meaningful
scanner logic, a Flask application, payment plumbing, and a non-trivial test
suite. It is not yet safe or coherent enough for a buyer-facing production
claim.

Current classification: **working prototype, not buyer-ready**

## Repair Progress

The 2026-06-13 local hardening pass completed these audit items:

- corrected Flask decorator order and added anonymous-denial tests;
- added signed, expiring access tokens bound to scan IDs;
- protected direct Stripe scan operations and System 6 proof pages;
- split process liveness from database-aware readiness;
- made deployment target `main` and removed ignored test failures;
- replaced the inaccurate README with the executable revenue-leak contract;
- added an MIT license and a reproducible synthetic sample command;
- increased the passing suite from 36 to 42 tests;
- added a pinned dependency lock, a one-command isolated verifier, and a
  bounded reproducibility contract.

These changes remain local and have not been pushed or deployed.

## Verified Strengths

- A clean virtual environment installed from `requirements.txt`.
- All 42 tests passed in the working environment. The original 36-test suite
  also passed in a clean virtual
  environment.
- The project compiles successfully.
- The application factory starts. `/live` reports process liveness and
  `/health` now reports database-aware readiness.
- The bundled sample processes 94 rows and detects three revenue-leak patterns:
  discount drift, failed-payment neglect, and pricing inconsistency.
- The sample result reports $187,270 in input revenue and $38,313 in estimated
  leakage. These are synthetic demo values, not customer outcomes.
- Stripe webhook signatures are verified when a webhook secret is configured.
- Checkout creation uses idempotency support, and payment persistence has a
  unique Stripe session constraint.
- System 6 tests preserve synthetic-data boundaries and require evidence for
  claimed outcomes.
- The repository scan found placeholders but no committed live Stripe, SMTP,
  database, or private-key credential.

## Release Blockers

### Resolved locally: API-key protection was not applied to several routes

Several endpoints place `@_require_api_key` above `@api_bp.route`. Python
applies decorators from the bottom upward, so Flask registers the original
unprotected function before the authentication wrapper is created.

Affected surfaces include System 6 action reads and mutations and
`/api/save-results`.

Decorator order is corrected locally and regression tests prove anonymous
denial. Deployment remains pending.

### Resolved locally: Scan reports were retrievable without authorization

`/results/<scan_id>` and `/report/<scan_id>` retrieve financial findings using
only a scan identifier. The upload path is also unauthenticated by design.

Results, reports, result capture, and recovery checkout now require signed,
expiring access tokens bound to the scan ID. Multi-user tenant scoping,
retention rules, and deletion support remain required for broader deployment.

### Resolved locally: The public README described a different product

The README claims a production-grade FastAPI platform for attributing CSV data
exfiltration, field access, queries, downloads, and user liability. The code is
a Flask revenue-leak scanner and does not implement that forensic
instrumentation model.

The README also documents endpoints and response contracts that do not match
the registered Flask routes.

The local README now describes the revenue-leak evidence product that actually
exists. It has not been pushed.

### High: Pricing and fulfillment contracts conflict

The repository contains at least three incompatible commercial models:

- public docs: a $199 one-time evidence audit after fit confirmation;
- product document: 10% of recovered revenue plus retainers;
- application checkout: 10% self-serve or 20% done-with-you, subject to
  minimum fees, plus separate subscriptions.

One offer, price, scope, refund policy, and fulfillment contract must become
canonical before taking payment.

### Resolved locally: Deployment automation did not enforce correctness

The deploy workflow watches `master`, while the repository default branch is
`main`. Its test command also ends with `|| true`, allowing deployment after
test failure.

The local workflow now targets `main` and fails when tests fail.

### Resolved locally: No license was present

An MIT license is present locally and has not been pushed.

### Resolved locally: Production readiness reported while dependencies were dead

Application startup catches database initialization failures, and `/health`
still returns `OK`. This is useful for local UI work but unsafe as a production
readiness probe.

`/live` now reports process liveness. `/health` returns HTTP 503 when the
database is unavailable.

### Medium: Secret and rate-limit defaults are development-only

The application falls back to a known Flask secret and uses in-memory rate
limiting. Production must reject the default secret and use a shared rate-limit
backend when multiple workers are present.

### Partially resolved locally: Installation metadata is incomplete

The project still has no `pyproject.toml`, but now includes a pinned
`requirements-lock.txt`, a supported Python minimum, and
`scripts/verify_fresh_clone.sh`. Packaging metadata and a broader Python
compatibility matrix remain future work.

### Medium: Repository scope obscures the product

The top level mixes the buyer product with historical System 5 and System 6
reports, task records, backup dashboards, domain experiments, and deployment
notes. These may be valuable internally but make the supported product surface
unclear.

## Shortest Buyer-Ready Path

1. Repair and test authentication decorator placement.
2. Add authenticated ownership or signed expiring access for every scan and
   report.
3. Choose one commercial offer and make code, public docs, checkout, and terms
   agree.
4. Replace the README with a truthful revenue-leak product contract and a
   reproducible five-minute demo.
5. Make CI and deployment fail closed on `main`.
6. Add a license, packaging metadata, dependency constraints, and a supported
   Python version policy.
7. Separate liveness from dependency-aware readiness.
8. Move internal architecture history out of the primary buyer journey.
9. Run a security review using synthetic data before accepting any customer
   billing export.
10. Validate one controlled pilot and report measured detection accuracy,
    false positives, review time, and confirmed recoverable value.

## Buyer-Ready Exit Criteria

LeakLock should not be called buyer-ready until:

- unauthorized scan and action access is denied by automated tests;
- all public product and pricing claims match executable behavior;
- a new user can install and run the synthetic demo from the README;
- CI passes from a clean checkout and blocks deployment on failure;
- production readiness detects unavailable dependencies;
- privacy, retention, deletion, and incident-handling rules exist;
- at least one controlled pilot distinguishes estimated leakage from verified
  recovery.

