"""Run LeakLock against the bundled synthetic sample."""

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from csv_scanner import scan_csv


def main() -> int:
    result = scan_csv((ROOT / "static" / "sample_data.csv").read_bytes())
    summary = {
        "data_class": "synthetic",
        "rows_parsed": result.get("rows_parsed", 0),
        "total_revenue": result.get("total_revenue", 0),
        "estimated_leakage": result.get("total_leakage", 0),
        "patterns": sorted(
            {
                item.get("pattern") or item.get("pattern_name")
                for item in result.get("leaks", [])
                if item.get("pattern") or item.get("pattern_name")
            }
        ),
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

