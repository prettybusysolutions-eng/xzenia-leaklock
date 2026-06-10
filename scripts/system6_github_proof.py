#!/usr/bin/env python3
"""Build and optionally live-verify a System 6 GitHub consequence proof."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.github_consequence import build_operational_proof


def _gh_run(repo: str, run_id: str) -> dict:
    result = subprocess.run(
        [
            "gh", "run", "view", run_id, "--repo", repo,
            "--json", "databaseId,workflowName,conclusion,status,createdAt,updatedAt,headSha,url",
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"unable to fetch {repo} run {run_id}")
    data = json.loads(result.stdout)
    return {
        "repo": repo,
        "run_id": str(data["databaseId"]),
        "workflow_name": data["workflowName"],
        "conclusion": data["conclusion"],
        "status": data["status"],
        "created_at": data["createdAt"],
        "updated_at": data["updatedAt"],
        "head_sha": data["headSha"],
        "url": data["url"],
    }


def _verify_snapshot(snapshot: dict) -> list[str]:
    live = _gh_run(snapshot["repo"], snapshot["run_id"])
    fields = ("repo", "run_id", "workflow_name", "conclusion", "created_at", "updated_at", "head_sha", "url")
    return [
        f"{snapshot['repo']}#{snapshot['run_id']} field {field} differs from live GitHub"
        for field in fields
        if snapshot.get(field) != live.get(field)
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--verify-live", action="store_true")
    args = parser.parse_args()

    bundle = json.loads(args.input.read_text())
    report = build_operational_proof(bundle)
    live_errors = []
    if args.verify_live:
        for case in bundle.get("cases", []):
            live_errors.extend(_verify_snapshot(case))
        for intervention in bundle.get("interventions", []):
            live_errors.extend(_verify_snapshot(intervention["outcome"]))
    report["live_verification"] = {
        "requested": args.verify_live,
        "checked_snapshots": (
            len(bundle.get("cases", [])) + len(bundle.get("interventions", []))
            if args.verify_live else 0
        ),
        "valid": not live_errors,
        "errors": live_errors,
    }
    report["valid"] = report["valid"] and not live_errors

    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered)
    print(rendered, end="")
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
