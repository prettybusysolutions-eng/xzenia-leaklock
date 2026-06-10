"""System 5 v2 domain pack for operational reliability and incident diagnosis."""

from __future__ import annotations

from cognitive.domain_activation import (
    ActionPolicy,
    CausalMapping,
    DomainActivationPack,
    EvidenceRequirement,
    OntologyEntity,
)
from cognitive.domain_schema import (
    AnomalyRule,
    DomainDefinition,
    RecoveryAction,
    SignalDefinition,
)


def _service_unreachable(context: dict) -> bool:
    return context.get("reachable") is False


def _workflow_failed(context: dict) -> bool:
    return context.get("conclusion") in {
        "failure",
        "cancelled",
        "timed_out",
        "startup_failure",
    }


def _disk_critical(context: dict) -> bool:
    return context.get("used_percent", 0) >= 95


DOMAIN = DomainDefinition(
    domain_id="operational_reliability",
    display_name="Operational Reliability",
    version="2.0.0",
    description=(
        "Diagnoses service reachability, CI execution failures, and host capacity "
        "pressure while preserving evidence and human approval for risky recovery."
    ),
    owner="Aurex / Kamm Smith",
    status="experimental",
    signals=[
        SignalDefinition(
            name="component_health_observed",
            description="A bounded health probe observed a component state.",
            schema={
                "component_id": "str",
                "reachable": "bool",
                "observed_at": "datetime",
                "source_ref": "str",
            },
        ),
        SignalDefinition(
            name="workflow_run_completed",
            description="A CI workflow completed with a stable external run identifier.",
            schema={
                "repository": "str",
                "run_id": "str",
                "head_sha": "str",
                "conclusion": "str",
                "observed_at": "datetime",
                "source_ref": "str",
            },
        ),
        SignalDefinition(
            name="disk_capacity_observed",
            description="A host volume reported used capacity and remaining free space.",
            schema={
                "host_id": "str",
                "mount": "str",
                "used_percent": "int",
                "free_gib": "float",
                "observed_at": "datetime",
                "source_ref": "str",
            },
        ),
    ],
    anomaly_rules=[
        AnomalyRule(
            rule_id="component_unreachable",
            description="A required component cannot be reached by its bounded probe.",
            severity="critical",
            check_fn=_service_unreachable,
        ),
        AnomalyRule(
            rule_id="workflow_execution_failed",
            description="A CI workflow ended without a successful conclusion.",
            severity="high",
            check_fn=_workflow_failed,
        ),
        AnomalyRule(
            rule_id="disk_capacity_critical",
            description="A writable volume is at or above 95 percent utilization.",
            severity="critical",
            check_fn=_disk_critical,
        ),
    ],
    recovery_actions=[
        RecoveryAction(
            action_id="collect_bounded_diagnostics",
            description="Collect read-only health, logs, and configuration evidence.",
            requires_approval=False,
        ),
        RecoveryAction(
            action_id="propose_code_repair",
            description="Prepare a scoped code repair for the evidenced workflow failure.",
            requires_approval=True,
        ),
        RecoveryAction(
            action_id="preserve_recovery_evidence",
            description="Preserve manifests and recovery configuration before cleanup.",
            requires_approval=False,
        ),
        RecoveryAction(
            action_id="remove_approved_disk_residue",
            description="Remove only the exact disk residue approved by the human.",
            requires_approval=True,
        ),
    ],
    data_sources=[
        "openclaw:status",
        "github:workflow_runs",
        "host:disk_usage",
    ],
    tags=["operations", "incident-response", "ci", "capacity", "evidence"],
    metadata={"system5_version": 2, "external_state_gated": True},
    health_check_fn=lambda: {
        "status": "ok",
        "message": "Operational reliability pack is registered.",
    },
)


PACK = DomainActivationPack(
    domain=DOMAIN,
    ontology=[
        OntologyEntity("component", "component_id", "A service or runtime component."),
        OntologyEntity("workflow_run", "run_id", "A stable CI execution."),
        OntologyEntity("host_volume", "mount", "A writable host storage volume."),
        OntologyEntity("incident", "source_ref", "An evidenced operational failure."),
    ],
    evidence_requirements=[
        EvidenceRequirement(
            requirement_id="component_probe",
            description="Reachability proof from a bounded component probe.",
            required_fields=["component_id", "reachable", "observed_at", "source_ref"],
        ),
        EvidenceRequirement(
            requirement_id="workflow_run",
            description="Stable workflow identity and conclusion evidence.",
            required_fields=[
                "repository",
                "run_id",
                "head_sha",
                "conclusion",
                "source_ref",
            ],
        ),
        EvidenceRequirement(
            requirement_id="disk_measurement",
            description="Measured host volume pressure from the operating system.",
            required_fields=[
                "host_id",
                "mount",
                "used_percent",
                "free_gib",
                "source_ref",
            ],
        ),
    ],
    causal_mappings=[
        CausalMapping(
            rule_id="component_unreachable",
            signal_name="component_health_observed",
            cause_entity="component",
            effect_entity="incident",
            hypothesis="The component is unavailable or its execution path is stalled.",
            evidence_requirement_ids=["component_probe"],
            action_ids=["collect_bounded_diagnostics"],
        ),
        CausalMapping(
            rule_id="workflow_execution_failed",
            signal_name="workflow_run_completed",
            cause_entity="workflow_run",
            effect_entity="incident",
            hypothesis="A code, configuration, dependency, or test defect blocked CI.",
            evidence_requirement_ids=["workflow_run"],
            action_ids=["collect_bounded_diagnostics", "propose_code_repair"],
        ),
        CausalMapping(
            rule_id="disk_capacity_critical",
            signal_name="disk_capacity_observed",
            cause_entity="host_volume",
            effect_entity="incident",
            hypothesis="Accumulated residue or active data exhausted safe disk headroom.",
            evidence_requirement_ids=["disk_measurement"],
            action_ids=["preserve_recovery_evidence", "remove_approved_disk_residue"],
        ),
    ],
    action_policies=[
        ActionPolicy(
            action_id="collect_bounded_diagnostics",
            risk_level="low",
            approval_required=False,
            verification_fields=["diagnostic_bundle_ref", "collected_at"],
        ),
        ActionPolicy(
            action_id="propose_code_repair",
            risk_level="medium",
            approval_required=True,
            verification_fields=["commit_sha", "test_run_id"],
        ),
        ActionPolicy(
            action_id="preserve_recovery_evidence",
            risk_level="low",
            approval_required=False,
            verification_fields=["manifest_path", "sha256_ref"],
        ),
        ActionPolicy(
            action_id="remove_approved_disk_residue",
            risk_level="critical",
            approval_required=True,
            verification_fields=["approval_message_id", "space_before", "space_after"],
        ),
    ],
)
