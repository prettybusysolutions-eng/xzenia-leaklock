"""
domains/github_ops_domain.py
Xzenia Domain Definition — GitHub Operations

A public, externally attested consequence domain for Xzenia.
Uses GitHub issues, pull requests, reviews, and workflow runs as
stable-ID reality hooks before private business data is available.
"""

from __future__ import annotations

from cognitive.domain_schema import (
    AnomalyRule,
    DomainDefinition,
    RecoveryAction,
    SignalDefinition,
)


def _make_signals():
    return [
        SignalDefinition(
            name="github_issue_opened",
            description="A GitHub issue exists as an externally addressable work item.",
            schema={
                "repo": "str",
                "issue_number": "int",
                "issue_id": "str",
                "title": "str",
                "state": "str",
                "created_at": "datetime",
            },
        ),
        SignalDefinition(
            name="github_pull_request_opened",
            description="A pull request exists as an externally addressable intervention candidate.",
            schema={
                "repo": "str",
                "pr_number": "int",
                "pr_id": "str",
                "head_sha": "str",
                "state": "str",
                "created_at": "datetime",
            },
        ),
        SignalDefinition(
            name="github_workflow_run_completed",
            description="A workflow run completed and can attest execution success or failure.",
            schema={
                "repo": "str",
                "run_id": "str",
                "workflow_name": "str",
                "conclusion": "str",
                "completed_at": "datetime",
            },
        ),
        SignalDefinition(
            name="github_review_submitted",
            description="A review decision exists as an externally visible approval or rejection artifact.",
            schema={
                "repo": "str",
                "pr_number": "int",
                "review_id": "str",
                "state": "str",
                "submitted_at": "datetime",
            },
        ),
    ]


def _stale_issue_check(context: dict) -> bool:
    return context.get("days_open", 0) > 7 and context.get("state") == "open"


def _failing_ci_check(context: dict) -> bool:
    return context.get("conclusion") in {"failure", "cancelled", "timed_out", "startup_failure"}


def _make_anomaly_rules():
    return [
        AnomalyRule(
            rule_id="stale_open_issue",
            description="Issue remains open beyond expected SLA and may represent execution backlog.",
            severity="medium",
            check_fn=_stale_issue_check,
        ),
        AnomalyRule(
            rule_id="failing_ci_run",
            description="Workflow run concluded unsuccessfully and blocks externally verifiable progress.",
            severity="high",
            check_fn=_failing_ci_check,
        ),
        AnomalyRule(
            rule_id="unreviewed_pull_request",
            description="Pull request is open without review feedback, blocking decision closure.",
            severity="medium",
            check_fn=None,
        ),
    ]


def _make_recovery_actions():
    return [
        RecoveryAction(
            action_id="propose_pull_request",
            description="Create or update a pull request addressing a GitHub issue. Requires human approval.",
            requires_approval=True,
        ),
        RecoveryAction(
            action_id="request_review",
            description="Request human review on an open pull request. Requires approval.",
            requires_approval=True,
        ),
        RecoveryAction(
            action_id="retry_workflow",
            description="Retry a failed workflow run where policy allows. Requires approval.",
            requires_approval=True,
        ),
        RecoveryAction(
            action_id="log_attested_outcome",
            description="Record externally verified issue/PR/workflow outcome in the consequence loop.",
            requires_approval=False,
        ),
    ]


def _health_check() -> dict:
    return {
        "status": "ok",
        "message": "GitHub operations domain registered. External readiness depends on gh auth and repo target.",
    }


DOMAIN = DomainDefinition(
    domain_id="github_ops",
    display_name="GitHub Operations",
    version="1.0.0",
    description=(
        "Uses GitHub issues, pull requests, reviews, and workflow runs as an externally "
        "attested consequence domain for Xzenia. Designed to bind action, approval, "
        "execution, and outcome to stable public identifiers."
    ),
    owner="Aurex / Kamm Smith",
    status="experimental",
    signals=_make_signals(),
    anomaly_rules=_make_anomaly_rules(),
    recovery_actions=_make_recovery_actions(),
    data_sources=["github:issues", "github:pull_requests", "github:workflow_runs", "gh_cli"],
    tags=["github", "attestation", "consequence", "verification", "public-ids"],
    metadata={
        "verification_domain": True,
        "public_attestation": True,
        "requires_gh_auth": True,
    },
    health_check_fn=_health_check,
)
