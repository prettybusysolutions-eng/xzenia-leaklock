# System 5 — Generalized Domain Onboarding Contract ✅

**Completed:** 2026-03-29  
**Status:** COMPLETE — Both domains pass with zero violations

---

## What Was Built

System 5 establishes a substrate-agnostic contract that any domain must satisfy
before activation in the Xzenia cognitive loop. It separates domain *declaration*
from domain *infrastructure*, enabling any business area to onboard through the
same validator without modifying the substrate.

### Files Created

| File | Purpose |
|------|---------|
| `cognitive/domain_schema.py` | `DomainDefinition` dataclass — the universal contract |
| `cognitive/domain_onboarding_contract.py` | System 5 validator — 6 rule categories |
| `cognitive/onboard_domain.py` | CLI runner — `python -m cognitive.onboard_domain <module>` |
| `domains/revenue_recovery_domain.py` | Revenue recovery domain — passes with 0 violations |
| `domains/pretty_busy_cleaning_domain.py` | Cleaning ops domain — passes with 0 violations |

---

## Validator Output

### Revenue Recovery Domain
```
✅ PASS — Domain: revenue_recovery
  Violations : 0
  Warnings   : 2  (deferred check_fn implementations — expected)
  ✅ Domain 'Revenue Recovery' is cleared for activation.
```

### Pretty Busy Cleaning Domain
```
✅ PASS — Domain: pretty_busy_cleaning
  Violations : 0
  Warnings   : 3  (deferred check_fn implementations — expected)
  ✅ Domain 'Pretty Busy Cleaning' is cleared for activation.
```

---

## Contract Rules (6 categories)

1. **Identity** — `domain_id` slug, `display_name`, semver `version`, min-length `description`, `owner`, valid `status`
2. **Signals** — ≥1 signal; each has slug name, description, non-empty schema; no duplicates
3. **Anomaly Rules** — ≥1 rule; each has slug id, description, valid severity; callable or None check_fn
4. **Recovery Actions** — ≥1 action; each has slug id, description; callable or None execute_fn
5. **Data Sources** — warned if empty; each entry must be a non-empty string
6. **Health Check** — warned if absent; must be callable if present

Warnings are non-blocking. Violations block activation.

---

## Key Design Properties

- **Zero substrate coupling** — the validator imports nothing from Stripe, PostgreSQL, or any domain-specific lib
- **Two-tier feedback** — violations (blocking) vs warnings (advisory, e.g. deferred check_fn)
- **Human approval gates** — `RecoveryAction.requires_approval=True` by default; auto-execute only when explicitly safe
- **Extensible** — new domains implement `DomainDefinition` and run `onboard_domain` — no validator changes needed

---

## Definition of Done — Verified

- [x] Revenue recovery domain passes validator with **zero violations**
- [x] Pretty Busy Cleaning onboards through **same validator** with **zero substrate modification**
- [x] CLI runner works: `python -m cognitive.onboard_domain <module>`
- [x] Git commit: `feat: System 5 — Generalized Domain Onboarding Contract complete`
