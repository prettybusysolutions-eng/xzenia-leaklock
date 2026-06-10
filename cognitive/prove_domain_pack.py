#!/usr/bin/env python3
"""Validate a System 5 v2 pack and evaluate an evidence case file."""

from __future__ import annotations

import argparse
import importlib
import json
from datetime import datetime, timezone
from pathlib import Path

from cognitive.domain_activation import (
    activate_pack,
    DomainActivationContract,
    DomainActivationPack,
    evaluate_signal,
)


def prove(module_path: str, cases_path: Path) -> dict:
    module = importlib.import_module(module_path)
    pack = getattr(module, "PACK", None)
    if not isinstance(pack, DomainActivationPack):
        raise TypeError(f"{module_path} does not expose a DomainActivationPack named PACK")

    validation = DomainActivationContract().validate(pack)
    activation = activate_pack(pack)
    cases = json.loads(cases_path.read_text())
    results = []
    if validation.passed:
        for case in cases["cases"]:
            result = evaluate_signal(
                pack,
                case["signal_name"],
                case["payload"],
                case.get("context") or {},
                case.get("evidence") or {},
            )
            results.append({"case_id": case["case_id"], **result})

    return {
        "kind": "xzenia.system5-v2.proof-report",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "module": module_path,
        "validation": validation.summary(),
        "activation": activation,
        "summary": {
            "cases": len(results),
            "accepted": sum(item["accepted"] for item in results),
            "findings": sum(len(item["findings"]) for item in results),
            "executed_actions": 0,
        },
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("module")
    parser.add_argument("--cases", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    arguments = parser.parse_args()
    report = prove(arguments.module, arguments.cases)
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report["summary"], sort_keys=True))
    return 0 if report["activation"]["activated"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
