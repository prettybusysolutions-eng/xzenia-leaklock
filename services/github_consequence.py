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
from typing import Any, Dict, Optional


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
    'readiness_json',
    'domain_case_json',
]


if __name__ == '__main__':
    print(readiness_json())
