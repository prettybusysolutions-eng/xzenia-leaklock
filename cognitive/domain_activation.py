"""
System 5 v2 domain activation contract.

System 5 v1 validates that a domain declaration is structurally complete.
This module adds the evidence, causal, risk, and verification surfaces required
to prove that a declared domain can enter the cognitive loop safely.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from cognitive.domain_onboarding_contract import DomainOnboardingContract, Violation
from cognitive.domain_schema import DomainDefinition


VALID_RISK_LEVELS = {"low", "medium", "high", "critical"}


@dataclass(frozen=True)
class OntologyEntity:
    entity_type: str
    id_field: str
    description: str


@dataclass(frozen=True)
class EvidenceRequirement:
    requirement_id: str
    description: str
    required_fields: List[str]
    min_sources: int = 1


@dataclass(frozen=True)
class CausalMapping:
    rule_id: str
    signal_name: str
    cause_entity: str
    effect_entity: str
    hypothesis: str
    evidence_requirement_ids: List[str]
    action_ids: List[str]


@dataclass(frozen=True)
class ActionPolicy:
    action_id: str
    risk_level: str
    approval_required: bool
    verification_fields: List[str]


@dataclass
class DomainActivationPack:
    domain: DomainDefinition
    ontology: List[OntologyEntity] = field(default_factory=list)
    evidence_requirements: List[EvidenceRequirement] = field(default_factory=list)
    causal_mappings: List[CausalMapping] = field(default_factory=list)
    action_policies: List[ActionPolicy] = field(default_factory=list)


@dataclass
class PackValidationResult:
    domain_id: str
    passed: bool
    violations: List[Violation] = field(default_factory=list)
    warnings: List[Violation] = field(default_factory=list)

    def summary(self) -> Dict[str, Any]:
        return {
            "domain_id": self.domain_id,
            "passed": self.passed,
            "violation_count": len(self.violations),
            "warning_count": len(self.warnings),
            "violations": [
                {"field": item.field, "message": item.message}
                for item in self.violations
            ],
            "warnings": [
                {"field": item.field, "message": item.message}
                for item in self.warnings
            ],
        }


class DomainActivationContract:
    """Validate that a v1 domain can be activated without hidden domain logic."""

    def validate(self, pack: DomainActivationPack) -> PackValidationResult:
        base = DomainOnboardingContract().validate(pack.domain)
        violations = list(base.violations)
        warnings = list(base.warnings)

        def err(field: str, message: str) -> None:
            violations.append(Violation(field=field, message=message))

        if not pack.ontology:
            err("ontology", "activation pack must declare at least one entity")
        entity_types = {item.entity_type for item in pack.ontology}
        if len(entity_types) != len(pack.ontology):
            err("ontology", "entity_type values must be unique")
        for index, entity in enumerate(pack.ontology):
            if not entity.entity_type or not entity.id_field or not entity.description:
                err(f"ontology[{index}]", "entity type, id field, and description are required")

        requirements = {
            item.requirement_id: item for item in pack.evidence_requirements
        }
        if not requirements:
            err("evidence_requirements", "at least one evidence requirement is required")
        if len(requirements) != len(pack.evidence_requirements):
            err("evidence_requirements", "requirement_id values must be unique")
        for index, requirement in enumerate(pack.evidence_requirements):
            if not requirement.required_fields:
                err(
                    f"evidence_requirements[{index}].required_fields",
                    "must not be empty",
                )
            if requirement.min_sources < 1:
                err(
                    f"evidence_requirements[{index}].min_sources",
                    "must be at least one",
                )

        signals = {item.name for item in pack.domain.signals}
        rules = {item.rule_id: item for item in pack.domain.anomaly_rules}
        actions = {item.action_id: item for item in pack.domain.recovery_actions}
        mappings = {item.rule_id: item for item in pack.causal_mappings}
        policies = {item.action_id: item for item in pack.action_policies}
        if len(mappings) != len(pack.causal_mappings):
            err("causal_mappings", "rule_id values must be unique")
        if len(policies) != len(pack.action_policies):
            err("action_policies", "action_id values must be unique")

        if set(rules) != set(mappings):
            missing = sorted(set(rules) - set(mappings))
            unknown = sorted(set(mappings) - set(rules))
            if missing:
                err("causal_mappings", f"rules without causal mappings: {missing}")
            if unknown:
                err("causal_mappings", f"mappings reference unknown rules: {unknown}")

        for index, mapping in enumerate(pack.causal_mappings):
            prefix = f"causal_mappings[{index}]"
            if mapping.signal_name not in signals:
                err(prefix + ".signal_name", f"unknown signal {mapping.signal_name!r}")
            if mapping.cause_entity not in entity_types:
                err(prefix + ".cause_entity", f"unknown entity {mapping.cause_entity!r}")
            if mapping.effect_entity not in entity_types:
                err(prefix + ".effect_entity", f"unknown entity {mapping.effect_entity!r}")
            if not mapping.hypothesis.strip():
                err(prefix + ".hypothesis", "must not be empty")
            for requirement_id in mapping.evidence_requirement_ids:
                if requirement_id not in requirements:
                    err(
                        prefix + ".evidence_requirement_ids",
                        f"unknown requirement {requirement_id!r}",
                    )
            for action_id in mapping.action_ids:
                if action_id not in actions:
                    err(prefix + ".action_ids", f"unknown action {action_id!r}")

        if set(actions) != set(policies):
            missing = sorted(set(actions) - set(policies))
            unknown = sorted(set(policies) - set(actions))
            if missing:
                err("action_policies", f"actions without policy: {missing}")
            if unknown:
                err("action_policies", f"policies reference unknown actions: {unknown}")

        for index, policy in enumerate(pack.action_policies):
            prefix = f"action_policies[{index}]"
            if policy.risk_level not in VALID_RISK_LEVELS:
                err(prefix + ".risk_level", f"invalid risk level {policy.risk_level!r}")
            action = actions.get(policy.action_id)
            if action and policy.approval_required != action.requires_approval:
                err(
                    prefix + ".approval_required",
                    "policy must match the domain recovery action",
                )
            if policy.risk_level in {"high", "critical"} and not policy.approval_required:
                err(prefix, "high and critical risk actions require human approval")
            if not policy.verification_fields:
                err(prefix + ".verification_fields", "must not be empty")

        for rule_id, rule in rules.items():
            if rule.check_fn is None:
                err(
                    f"anomaly_rules.{rule_id}.check_fn",
                    "activation requires an executable rule",
                )

        return PackValidationResult(
            domain_id=pack.domain.domain_id,
            passed=not violations,
            violations=violations,
            warnings=warnings,
        )


def activate_pack(pack: DomainActivationPack) -> Dict[str, Any]:
    """Validate the pack and run its read-only health check."""
    validation = DomainActivationContract().validate(pack)
    if not validation.passed:
        return {
            "activated": False,
            "validation": validation.summary(),
            "health": None,
        }
    health = pack.domain.health_check_fn()
    valid_health = (
        isinstance(health, dict)
        and health.get("status") in {"ok", "degraded", "down"}
        and isinstance(health.get("message"), str)
    )
    if not valid_health:
        return {
            "activated": False,
            "validation": validation.summary(),
            "health": health,
            "error": "health check returned an invalid contract",
        }
    return {
        "activated": health["status"] == "ok",
        "validation": validation.summary(),
        "health": health,
    }


def _value_matches(value: Any, declared_type: str) -> bool:
    types = {
        "str": str,
        "int": int,
        "float": (int, float),
        "bool": bool,
        "dict": dict,
        "list": list,
        "datetime": str,
    }
    if declared_type in {"int", "float"} and isinstance(value, bool):
        return False
    expected = types.get(declared_type)
    return expected is not None and isinstance(value, expected)


def evaluate_signal(
    pack: DomainActivationPack,
    signal_name: str,
    payload: Dict[str, Any],
    context: Dict[str, Any],
    evidence: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Evaluate one signal without executing recovery actions.

    The output is a proposal surface only. Approval and execution remain outside
    this function.
    """
    validation = DomainActivationContract().validate(pack)
    if not validation.passed:
        raise ValueError(validation.summary())

    signals = {item.name: item for item in pack.domain.signals}
    if signal_name not in signals:
        raise ValueError(f"unknown signal {signal_name!r}")

    signal = signals[signal_name]
    schema_errors = []
    for field_name, field_type in signal.schema.items():
        if field_name not in payload:
            schema_errors.append(f"missing payload field {field_name!r}")
        elif not _value_matches(payload[field_name], field_type):
            schema_errors.append(
                f"payload field {field_name!r} does not match {field_type!r}"
            )
    if schema_errors:
        return {
            "domain_id": pack.domain.domain_id,
            "signal_name": signal_name,
            "accepted": False,
            "errors": schema_errors,
            "findings": [],
        }

    rules = {item.rule_id: item for item in pack.domain.anomaly_rules}
    actions = {item.action_id: item for item in pack.domain.recovery_actions}
    policies = {item.action_id: item for item in pack.action_policies}
    requirements = {
        item.requirement_id: item for item in pack.evidence_requirements
    }
    merged_context = {**payload, **context}
    findings = []

    for mapping in pack.causal_mappings:
        if mapping.signal_name != signal_name:
            continue
        rule = rules[mapping.rule_id]
        if not rule.check_fn(merged_context):
            continue

        missing_evidence = []
        for requirement_id in mapping.evidence_requirement_ids:
            requirement = requirements[requirement_id]
            item = evidence.get(requirement_id) or {}
            absent = [
                field_name
                for field_name in requirement.required_fields
                if item.get(field_name) in (None, "")
            ]
            sources = item.get("sources") or []
            if absent or len(sources) < requirement.min_sources:
                missing_evidence.append(
                    {
                        "requirement_id": requirement_id,
                        "missing_fields": absent,
                        "sources_required": requirement.min_sources,
                        "sources_present": len(sources),
                    }
                )

        evidence_complete = not missing_evidence
        proposals = []
        for action_id in mapping.action_ids:
            action = actions[action_id]
            policy = policies[action_id]
            proposals.append(
                {
                    "action_id": action_id,
                    "description": action.description,
                    "risk_level": policy.risk_level,
                    "approval_required": policy.approval_required,
                    "verification_fields": policy.verification_fields,
                    "status": (
                        "blocked_missing_evidence"
                        if not evidence_complete
                        else "awaiting_approval"
                        if policy.approval_required
                        else "ready_for_governed_execution"
                    ),
                }
            )

        findings.append(
            {
                "rule_id": mapping.rule_id,
                "severity": rule.severity,
                "hypothesis": mapping.hypothesis,
                "cause_entity": mapping.cause_entity,
                "effect_entity": mapping.effect_entity,
                "evidence_complete": evidence_complete,
                "missing_evidence": missing_evidence,
                "action_proposals": proposals,
            }
        )

    return {
        "domain_id": pack.domain.domain_id,
        "signal_name": signal_name,
        "accepted": True,
        "errors": [],
        "findings": findings,
    }
