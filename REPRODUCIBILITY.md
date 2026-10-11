# LeakLock Reproducibility

This document defines the bounded verification claim for the current LeakLock
prototype.

## Claim

From a fresh clone, a reviewer with Python 3.11 or newer and network access to
Python package indexes can:

1. install the pinned dependency set in an isolated virtual environment;
2. compile the source;
3. pass the automated test suite without PostgreSQL, Stripe, SMTP, or secrets;
4. run the bundled synthetic revenue-leak sample;
5. prove production configuration rejects the known development secret.

This does not prove production readiness, detection accuracy on customer data,
commercial demand, recoverability of estimated leakage, or healthcare
compliance.

## One-Command Verification

```bash
./scripts/verify_fresh_clone.sh
```

Success ends with:

```text
LEAKLOCK_FRESH_CLONE_VERIFIED
```

The synthetic sample is expected to report:

- `data_class`: `synthetic`
- `rows_parsed`: `94`
- patterns:
  - `discount_drift`
  - `failed_payment_neglect`
  - `pricing_inconsistency`

The dollar values are synthetic demonstration output and are not evidence of
customer value or recoverable revenue.

## Dependency Boundary

- `requirements.txt` expresses the supported direct dependency ranges.
- `requirements-lock.txt` records the exact dependency set used for this
  verification pass.
- The verifier creates and deletes its own temporary virtual environment.
- The verifier forces database traffic to an unavailable local port so passing
  tests cannot depend on the operator's PostgreSQL instance.

## Evidence Boundary

A successful run proves only the local software behavior listed above. Before
handling customer exports, LeakLock still requires a controlled security
review, a canonical commercial contract, enforced retention/deletion
operations, and a measured pilot.

