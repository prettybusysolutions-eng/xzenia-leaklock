import copy

from cognitive.domain_activation import (
    activate_pack,
    DomainActivationContract,
    evaluate_signal,
)
from cognitive.domain_onboarding_contract import DomainOnboardingContract
from domains.operational_reliability_domain import PACK
from domains.pretty_busy_cleaning_domain import DOMAIN as CLEANING_DOMAIN
from domains.revenue_recovery_domain import DOMAIN as REVENUE_DOMAIN


def _workflow_payload():
    return {
        "repository": "prettybusysolutions-eng/platform-spine",
        "run_id": "27299464728",
        "head_sha": "f82cdddb8188df65edf018580838d5fa8da3b70c",
        "conclusion": "failure",
        "observed_at": "2026-06-10T19:05:06Z",
        "source_ref": "https://github.com/example/run/27299464728",
    }


def _workflow_evidence():
    return {
        "workflow_run": {
            **_workflow_payload(),
            "sources": ["github-actions-log"],
        }
    }


def test_v1_domains_remain_valid_without_modification():
    contract = DomainOnboardingContract()
    assert contract.validate(REVENUE_DOMAIN).passed
    assert contract.validate(CLEANING_DOMAIN).passed


def test_operational_reliability_pack_passes_v2_contract():
    result = DomainActivationContract().validate(PACK)
    assert result.passed, result.summary()
    assert not result.violations
    activation = activate_pack(PACK)
    assert activation["activated"]
    assert activation["health"]["status"] == "ok"


def test_real_workflow_failure_produces_evidenced_gated_repair():
    result = evaluate_signal(
        PACK,
        "workflow_run_completed",
        _workflow_payload(),
        {"failed_test": "work registry creates resumable envelopes"},
        _workflow_evidence(),
    )
    assert result["accepted"]
    assert len(result["findings"]) == 1
    finding = result["findings"][0]
    assert finding["rule_id"] == "workflow_execution_failed"
    assert finding["evidence_complete"]
    proposals = {item["action_id"]: item for item in finding["action_proposals"]}
    assert proposals["collect_bounded_diagnostics"]["status"] == "ready_for_governed_execution"
    assert proposals["propose_code_repair"]["status"] == "awaiting_approval"


def test_disk_cleanup_is_never_proposed_without_human_approval_gate():
    payload = {
        "host_id": "host",
        "mount": "/System/Volumes/Data",
        "used_percent": 97,
        "free_gib": 3.7,
        "observed_at": "2026-06-10T19:14:39Z",
        "source_ref": "telegram-approval-13174",
    }
    evidence = {
        "disk_measurement": {
            **payload,
            "sources": ["df-output"],
        }
    }
    result = evaluate_signal(PACK, "disk_capacity_observed", payload, {}, evidence)
    proposals = {
        item["action_id"]: item
        for item in result["findings"][0]["action_proposals"]
    }
    cleanup = proposals["remove_approved_disk_residue"]
    assert cleanup["risk_level"] == "critical"
    assert cleanup["approval_required"]
    assert cleanup["status"] == "awaiting_approval"


def test_missing_evidence_blocks_all_action_proposals():
    result = evaluate_signal(
        PACK,
        "workflow_run_completed",
        _workflow_payload(),
        {},
        {},
    )
    finding = result["findings"][0]
    assert not finding["evidence_complete"]
    assert {
        item["status"] for item in finding["action_proposals"]
    } == {"blocked_missing_evidence"}


def test_signal_schema_rejects_boolean_as_integer():
    payload = {
        "host_id": "host",
        "mount": "/System/Volumes/Data",
        "used_percent": True,
        "free_gib": 3.7,
        "observed_at": "2026-06-10T19:14:39Z",
        "source_ref": "measurement",
    }
    result = evaluate_signal(PACK, "disk_capacity_observed", payload, {}, {})
    assert not result["accepted"]
    assert "does not match 'int'" in result["errors"][0]


def test_critical_action_without_approval_is_rejected():
    invalid = copy.deepcopy(PACK)
    policy = next(
        item
        for item in invalid.action_policies
        if item.action_id == "remove_approved_disk_residue"
    )
    invalid.action_policies[invalid.action_policies.index(policy)] = type(policy)(
        action_id=policy.action_id,
        risk_level=policy.risk_level,
        approval_required=False,
        verification_fields=policy.verification_fields,
    )
    result = DomainActivationContract().validate(invalid)
    assert not result.passed
    assert any("human approval" in item.message for item in result.violations)
