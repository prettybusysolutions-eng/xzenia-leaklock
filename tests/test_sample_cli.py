import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_sample_cli_reports_only_synthetic_summary():
    completed = subprocess.run(
        [sys.executable, "scripts/scan_sample.py"],
        cwd=ROOT,
        capture_output=True,
        check=True,
        text=True,
    )
    summary = json.loads(completed.stdout)
    assert summary["data_class"] == "synthetic"
    assert summary["rows_parsed"] > 0
    assert summary["patterns"]

