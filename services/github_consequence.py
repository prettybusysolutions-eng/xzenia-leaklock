"""GitHub-first consequence loop helpers.

This is the first externally attested domain scaffold for Xzenia when private
business identifiers are unavailable. It does not fake GitHub state; it only
reports readiness, normalizes stable IDs, and defines what counts as an
attestable case/action/outcome.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any, Dict, Optional
from urllib.parse import urlparse


@dataclass
class GitHubReadiness:
    gh_installed: bool
    gh_authenticated: bool
    repo_remote_present: bool
    current_repo: Optional[str]
    notes: list[str]


@dataclass
class GitHubConsequenceCase:
    domain: str
    source_system: str
    source_event_id: str
    anomaly_type: str
    evidence: Dict[str, Any]
    recommendation: str
    verification_path: str


REQUIRED_RUN_FIELDS = {
    "repo",
    "run_id",
    "workflow_name",
    "conclusion",
    "created_at",
    "updated_at",
    "head_sha",
    "url",
}


def _parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _valid_github_run_url(url: str, repo: str, run_id: str) -> bool:
    parsed = urlparse(url)
    return (
        parsed.scheme == "https"
        and parsed.netloc == "github.com"
        and parsed.path == f"/{repo}/actions/runs/{run_id}"
    )


def validate_workflow_run(run: Dict[str, Any], expected_conclusion: str) -> list[str]:
    """Validate one externally addressable GitHub workflow snapshot."""
    errors: list[str] = []
    missing = sorted(REQUIRED_RUN_FIELDS - set(run))
    if missing:
        return [f"missing run fields: {', '.join(missing)}"]

    for field in REQUIRED_RUN_FIELDS:
        if not str(run.get(field) or "").strip():
            errors.append(f"run field {field} must not be empty")

    if run.get("conclusion") != expected_conclusion:
        errors.append(f"run conclusion must be {expected_conclusion}")

    run_id = str(run.get("run_id") or "")
    repo = str(run.get("repo") or "")
    if not run_id.isdigit():
        errors.append("run_id must be numeric")
    if not _valid_github_run_url(str(run.get("url") or ""), repo, run_id):
        errors.append("run URL must exactly match repo and run_id")

    try:
        created_at = _parse_time(str(run.get("created_at") or ""))
        updated_at = _parse_time(str(run.get("updated_at") or ""))
        if updated_at < created_at:
            errors.append("run updated_at must not precede created_at")
    except ValueError:
        errors.append("run timestamps must be ISO8601")

    return errors


def validate_intervention(intervention: Dict[str, Any], cases_by_id: Dict[str, Dict[str, Any]]) -> list[str]:
    """Reject consequence claims that are not bound to case, approval, execution, and outcome evidence."""
    errors: list[str] = []
    case_id = str(intervention.get("case_id") or "")
    source = cases_by_id.get(case_id)
    if not source:
        return [f"intervention references unknown case_id {case_id!r}"]

    approval = intervention.get("approval") or {}
    execution = intervention.get("execution") or {}
    outcome = intervention.get("outcome") or {}
    if not str(intervention.get("proposal") or "").strip():
        errors.append("intervention proposal must not be empty")
    required_approval = {"actor_id", "actor_type", "channel", "message_id", "approved_scope"}
    required_execution = {"commit_sha", "summary"}
    missing_approval = sorted(required_approval - set(approval))
    missing_execution = sorted(required_execution - set(execution))
    if missing_approval:
        errors.append(f"approval missing fields: {', '.join(missing_approval)}")
    if missing_execution:
        errors.append(f"execution missing fields: {', '.join(missing_execution)}")
    for field in required_approval:
        if field in approval and not str(approval.get(field) or "").strip():
            errors.append(f"approval field {field} must not be empty")
    for field in required_execution:
        if field in execution and not str(execution.get(field) or "").strip():
            errors.append(f"execution field {field} must not be empty")
    commit_sha = str(execution.get("commit_sha") or "")
    if commit_sha and (len(commit_sha) != 40 or any(char not in "0123456789abcdef" for char in commit_sha.lower())):
        errors.append("execution commit_sha must be a full hexadecimal SHA")

    outcome_errors = validate_workflow_run(outcome, "success")
    errors.extend(f"outcome: {error}" for error in outcome_errors)
    if outcome:
        if outcome.get("repo") != source.get("repo"):
            errors.append("outcome repo must match source repo")
        if outcome.get("workflow_name") != source.get("workflow_name"):
            errors.append("outcome workflow must match source workflow")
        try:
            if _parse_time(str(outcome.get("created_at"))) <= _parse_time(str(source.get("updated_at"))):
                errors.append("outcome run must begin after source failure completed")
        except (TypeError, ValueError):
            pass
        if execution.get("commit_sha") != outcome.get("head_sha"):
            errors.append("execution commit_sha must match outcome head_sha")

    return errors


def build_operational_proof(bundle: Dict[str, Any]) -> Dict[str, Any]:
    """Build a truth-bounded System 6 proof report from real GitHub evidence."""
    cases = bundle.get("cases") or []
    interventions = bundle.get("interventions") or []
    errors: list[str] = []
    cases_by_id: Dict[str, Dict[str, Any]] = {}

    for index, case in enumerate(cases):
        case_id = str(case.get("case_id") or "")
        if not case_id:
            errors.append(f"cases[{index}] missing case_id")
            continue
        if case_id in cases_by_id:
            errors.append(f"duplicate case_id: {case_id}")
        cases_by_id[case_id] = case
        errors.extend(f"{case_id}: {error}" for error in validate_workflow_run(case, "failure"))

    for intervention in interventions:
        errors.extend(validate_intervention(intervention, cases_by_id))

    recoveries = []
    for intervention in interventions:
        source = cases_by_id.get(str(intervention.get("case_id") or ""))
        outcome = intervention.get("outcome") or {}
        if not source or validate_intervention(intervention, cases_by_id):
            continue
        recovery_seconds = int((_parse_time(outcome["updated_at"]) - _parse_time(source["updated_at"])).total_seconds())
        recoveries.append({
            "case_id": intervention["case_id"],
            "repo": source["repo"],
            "source_run_id": source["run_id"],
            "outcome_run_id": outcome["run_id"],
            "recovery_seconds": recovery_seconds,
            "verification_url": outcome["url"],
        })

    return {
        "schema_version": "system6.github_ops.v1",
        "domain": "github_ops",
        "proof_boundary": {
            "proved": "externally verified operational consequence",
            "not_proved": "revenue recovery or monetary value",
            "monetary_value_claimed": False,
        },
        "counts": {
            "real_external_cases": len(cases),
            "governed_actions_proposed": len(interventions),
            "approved_actions_executed": len(recoveries),
            "verified_outcomes": len(recoveries),
        },
        "metrics": {
            "workflows_restored": len(recoveries),
            "total_recovery_seconds": sum(item["recovery_seconds"] for item in recoveries),
            "mean_recovery_seconds": (
                round(sum(item["recovery_seconds"] for item in recoveries) / len(recoveries), 2)
                if recoveries else None
            ),
        },
        "recoveries": recoveries,
        "valid": not errors,
        "errors": errors,
    }


def _run(cmd: list[str], cwd: Optional[str] = None) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)


def gh_readiness(repo_dir: Optional[str] = None) -> GitHubReadiness:
    notes: list[str] = []
    installed = _run(["bash", "-lc", "which gh >/dev/null 2>&1"]).returncode == 0
    authenticated = False
    current_repo = None
    repo_remote_present = False

    if not installed:
        notes.append("gh CLI not installed")
        return GitHubReadiness(False, False, False, None, notes)

    auth = _run(["gh", "auth", "status"])
    authenticated = auth.returncode == 0
    if not authenticated:
        notes.append("gh auth not configured")

    if repo_dir:
        remote = _run(["git", "remote", "get-url", "origin"], cwd=repo_dir)
        if remote.returncode == 0:
            repo_remote_present = True
            url = remote.stdout.strip()
            if url.endswith('.git'):
                url = url[:-4]
            current_repo = url.split(':', 1)[-1].replace('https://github.com/', '')
        else:
            notes.append("no git origin remote configured")

    return GitHubReadiness(installed, authenticated, repo_remote_present, current_repo, notes)


def github_issue_case(repo: str, issue_number: int, title: str, labels: Optional[list[str]] = None) -> GitHubConsequenceCase:
    labels = labels or []
    return GitHubConsequenceCase(
        domain="github_ops",
        source_system="github_issue",
        source_event_id=f"{repo}#issue-{issue_number}",
        anomaly_type="open_issue_requires_intervention",
        evidence={
            "repo": repo,
            "issue_number": issue_number,
            "title": title,
            "labels": labels,
            "evidence_type": "github_issue",
        },
        recommendation=f"Triage issue #{issue_number} in {repo} and propose a governed intervention path.",
        verification_path=f"github://{repo}/issues/{issue_number}",
    )


def github_pr_case(repo: str, pr_number: int, title: str, head_sha: str) -> GitHubConsequenceCase:
    return GitHubConsequenceCase(
        domain="github_ops",
        source_system="github_pull_request",
        source_event_id=f"{repo}#pr-{pr_number}@{head_sha[:12]}",
        anomaly_type="pull_request_requires_review_or_merge",
        evidence={
            "repo": repo,
            "pr_number": pr_number,
            "title": title,
            "head_sha": head_sha,
            "evidence_type": "github_pull_request",
        },
        recommendation=f"Review PR #{pr_number} in {repo}, record decision, and verify workflow outcomes before merge.",
        verification_path=f"github://{repo}/pull/{pr_number}",
    )


def github_workflow_case(repo: str, run_id: str, workflow_name: str, conclusion: str) -> GitHubConsequenceCase:
    return GitHubConsequenceCase(
        domain="github_ops",
        source_system="github_workflow_run",
        source_event_id=f"{repo}#run-{run_id}",
        anomaly_type="workflow_run_requires_attention",
        evidence={
            "repo": repo,
            "run_id": str(run_id),
            "workflow_name": workflow_name,
            "conclusion": conclusion,
            "evidence_type": "github_workflow_run",
        },
        recommendation=f"Inspect workflow run {run_id} in {repo} and retry or remediate only after governed review.",
        verification_path=f"github://{repo}/actions/runs/{run_id}",
    )


def readiness_json(repo_dir: Optional[str] = None) -> str:
    return json.dumps(asdict(gh_readiness(repo_dir)), indent=2)


def domain_case_json(case: GitHubConsequenceCase) -> str:
    return json.dumps(asdict(case), indent=2)


__all__ = [
    'GitHubReadiness',
    'GitHubConsequenceCase',
    'gh_readiness',
    'github_issue_case',
    'github_pr_case',
    'github_workflow_case',
    'validate_workflow_run',
    'validate_intervention',
    'build_operational_proof',
    'readiness_json',
    'domain_case_json',
]


if __name__ == '__main__':
    print(readiness_json())
