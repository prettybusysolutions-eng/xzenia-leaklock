"""
cognitive/domain_onboarding_contract.py
Xzenia System 5 — Generalized Domain Onboarding Validator

Validates that a DomainDefinition is complete, internally consistent,
and safe before it is activated in the Xzenia cognitive loop.

The validator is SUBSTRATE-AGNOSTIC: it does not know about Stripe, PostgreSQL,
cleaning schedules, or any other domain-specific infrastructure. It only checks
the contract surface declared in DomainDefinition.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List

from cognitive.domain_schema import DomainDefinition


# ── Constants ─────────────────────────────────────────────────────────────────

VALID_STATUSES = {"active", "inactive", "experimental"}
VALID_SEVERITIES = {"critical", "high", "medium", "low"}
SEMVER_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")
SLUG_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")


# ── Result types ──────────────────────────────────────────────────────────────

@dataclass
class Violation:
    field: str
    message: str
    severity: str = "error"   # "error" | "warning"

    def __str__(self) -> str:
        tag = "❌" if self.severity == "error" else "⚠️"
        return f"{tag} [{self.field}] {self.message}"


@dataclass
class ValidationResult:
    domain_id: str
    passed: bool
    violations: List[Violation] = field(default_factory=list)
    warnings: List[Violation] = field(default_factory=list)

    def summary(self) -> str:
        lines = [
            f"{'✅ PASS' if self.passed else '🚫 FAIL'} — Domain: {self.domain_id}",
            f"  Violations : {len(self.violations)}",
            f"  Warnings   : {len(self.warnings)}",
        ]
        if self.violations:
            lines.append("\n  Violations:")
            for v in self.violations:
                lines.append(f"    {v}")
        if self.warnings:
            lines.append("\n  Warnings:")
            for w in self.warnings:
                lines.append(f"    {w}")
        return "\n".join(lines)


# ── Validator ─────────────────────────────────────────────────────────────────

class DomainOnboardingContract:
    """
    System 5 Validator.

    Usage:
        contract = DomainOnboardingContract()
        result = contract.validate(my_domain)
        if not result.passed:
            raise RuntimeError(result.summary())
    """

    def validate(self, domain: DomainDefinition) -> ValidationResult:
        violations: List[Violation] = []
        warnings: List[Violation] = []

        def err(field: str, msg: str):
            violations.append(Violation(field=field, message=msg, severity="error"))

        def warn(field: str, msg: str):
            warnings.append(Violation(field=field, message=msg, severity="warning"))

        # ── 1. Identity checks ────────────────────────────────────────────────
        if not domain.domain_id:
            err("domain_id", "must not be empty")
        elif not SLUG_PATTERN.match(domain.domain_id):
            err("domain_id", f"must match ^[a-z][a-z0-9_]*$ — got '{domain.domain_id}'")

        if not domain.display_name or not domain.display_name.strip():
            err("display_name", "must not be empty")

        if not domain.version:
            err("version", "must not be empty")
        elif not SEMVER_PATTERN.match(domain.version):
            err("version", f"must be semver (X.Y.Z) — got '{domain.version}'")

        if not domain.description or len(domain.description.strip()) < 20:
            err("description", "must be at least 20 characters")

        if not domain.owner or not domain.owner.strip():
            err("owner", "must not be empty")

        if domain.status not in VALID_STATUSES:
            err("status", f"must be one of {VALID_STATUSES} — got '{domain.status}'")

        # ── 2. Signals ────────────────────────────────────────────────────────
        if not domain.signals:
            err("signals", "domain must declare at least one signal")
        else:
            seen_signal_names = set()
            for i, sig in enumerate(domain.signals):
                prefix = f"signals[{i}]"
                if not sig.name:
                    err(prefix + ".name", "signal name must not be empty")
                elif not SLUG_PATTERN.match(sig.name):
                    err(prefix + ".name", f"signal name must match slug pattern — got '{sig.name}'")
                elif sig.name in seen_signal_names:
                    err(prefix + ".name", f"duplicate signal name '{sig.name}'")
                else:
                    seen_signal_names.add(sig.name)

                if not sig.description or not sig.description.strip():
                    err(prefix + ".description", "signal description must not be empty")

                if not isinstance(sig.schema, dict) or not sig.schema:
                    err(prefix + ".schema", "signal must declare a non-empty schema dict")

        # ── 3. Anomaly rules ──────────────────────────────────────────────────
        if not domain.anomaly_rules:
            err("anomaly_rules", "domain must declare at least one anomaly rule")
        else:
            seen_rule_ids = set()
            for i, rule in enumerate(domain.anomaly_rules):
                prefix = f"anomaly_rules[{i}]"
                if not rule.rule_id:
                    err(prefix + ".rule_id", "must not be empty")
                elif not SLUG_PATTERN.match(rule.rule_id):
                    err(prefix + ".rule_id", f"must match slug pattern — got '{rule.rule_id}'")
                elif rule.rule_id in seen_rule_ids:
                    err(prefix + ".rule_id", f"duplicate rule_id '{rule.rule_id}'")
                else:
                    seen_rule_ids.add(rule.rule_id)

                if not rule.description or not rule.description.strip():
                    err(prefix + ".description", "must not be empty")

                if rule.severity not in VALID_SEVERITIES:
                    err(prefix + ".severity", f"must be one of {VALID_SEVERITIES} — got '{rule.severity}'")

                if rule.check_fn is None:
                    warn(prefix + ".check_fn", f"rule '{rule.rule_id}' has no check_fn (deferred implementation)")
                elif not callable(rule.check_fn):
                    err(prefix + ".check_fn", "must be callable or None")

        # ── 4. Recovery actions ───────────────────────────────────────────────
        if not domain.recovery_actions:
            err("recovery_actions", "domain must declare at least one recovery action")
        else:
            seen_action_ids = set()
            for i, action in enumerate(domain.recovery_actions):
                prefix = f"recovery_actions[{i}]"
                if not action.action_id:
                    err(prefix + ".action_id", "must not be empty")
                elif not SLUG_PATTERN.match(action.action_id):
                    err(prefix + ".action_id", f"must match slug pattern — got '{action.action_id}'")
                elif action.action_id in seen_action_ids:
                    err(prefix + ".action_id", f"duplicate action_id '{action.action_id}'")
                else:
                    seen_action_ids.add(action.action_id)

                if not action.description or not action.description.strip():
                    err(prefix + ".description", "must not be empty")

                if action.execute_fn is not None and not callable(action.execute_fn):
                    err(prefix + ".execute_fn", "must be callable or None")

        # ── 5. Data sources ───────────────────────────────────────────────────
        if not domain.data_sources:
            warn("data_sources", "no data sources declared — domain may be inert")
        else:
            for i, ds in enumerate(domain.data_sources):
                if not isinstance(ds, str) or not ds.strip():
                    err(f"data_sources[{i}]", "data source entry must be a non-empty string")

        # ── 6. Health check ───────────────────────────────────────────────────
        if domain.health_check_fn is None:
            warn("health_check_fn", "no health_check_fn — domain health is unobservable")
        elif not callable(domain.health_check_fn):
            err("health_check_fn", "must be callable or None")

        # ── Result ────────────────────────────────────────────────────────────
        passed = len(violations) == 0
        return ValidationResult(
            domain_id=domain.domain_id or "<unknown>",
            passed=passed,
            violations=violations,
            warnings=warnings,
        )
