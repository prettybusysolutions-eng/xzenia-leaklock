#!/usr/bin/env python3
"""
cognitive/onboard_domain.py
Xzenia System 5 — CLI runner for domain onboarding validation.

Usage:
    python -m cognitive.onboard_domain <module_path>

    where <module_path> is a Python module that exposes a top-level
    variable named `DOMAIN` of type DomainDefinition.

Examples:
    python -m cognitive.onboard_domain domains.revenue_recovery_domain
    python -m cognitive.onboard_domain domains.pretty_busy_cleaning_domain
"""

from __future__ import annotations

import importlib
import sys

from cognitive.domain_onboarding_contract import DomainOnboardingContract
from cognitive.domain_schema import DomainDefinition


def onboard(module_path: str) -> bool:
    """
    Load a domain module, validate it, and print results.
    Returns True if the domain passed validation, False otherwise.
    """
    print(f"\n{'='*60}")
    print(f"  Xzenia System 5 — Domain Onboarding Validator")
    print(f"  Module: {module_path}")
    print(f"{'='*60}\n")

    # ── Load module ───────────────────────────────────────────────────────────
    try:
        mod = importlib.import_module(module_path)
    except ModuleNotFoundError as e:
        print(f"❌ Cannot import module '{module_path}': {e}")
        return False

    # ── Extract DOMAIN ────────────────────────────────────────────────────────
    domain = getattr(mod, "DOMAIN", None)
    if domain is None:
        print(f"❌ Module '{module_path}' does not expose a top-level DOMAIN variable.")
        return False

    if not isinstance(domain, DomainDefinition):
        print(
            f"❌ DOMAIN in '{module_path}' is type {type(domain).__name__}, "
            f"expected DomainDefinition."
        )
        return False

    # ── Validate ──────────────────────────────────────────────────────────────
    contract = DomainOnboardingContract()
    result = contract.validate(domain)

    print(result.summary())
    print()

    if result.passed:
        print(f"  ✅ Domain '{domain.display_name}' is cleared for activation.")
    else:
        print(f"  🚫 Domain '{domain.display_name}' BLOCKED — fix all violations before activating.")

    print(f"\n{'='*60}\n")
    return result.passed


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    module_path = sys.argv[1]
    passed = onboard(module_path)
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
