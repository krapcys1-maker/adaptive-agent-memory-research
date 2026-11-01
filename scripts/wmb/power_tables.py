#!/usr/bin/env python3
"""Print the minimum detectable win rates of the sign test and the upper bounds after zero failures, the numbers every WMB threshold is sized from.

Usage: python scripts/wmb/power_tables.py [--json OUT.json]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from wmb import stats  # noqa: E402

DECISIVE = (24, 43, 60, 100, 160, 214, 240, 300, 480)
PROBES = (24, 100, 300, 500, 1000)


def tables() -> dict:
    return {"mde_win_rate_two_sided_5pct_power_80": {str(n): stats.mde_win_rate(n) for n in DECISIVE},
            "zero_failures_upper_bound_95_one_sided": {str(n): round(stats.zero_failure_upper_bound(n), 4) for n in PROBES},
            "wilson_95_of_a_half": {str(n): [round(x, 3) for x in stats.wilson(n // 2, n)] for n in (24, 100, 300)}}


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--json", type=Path)
    args = parser.parse_args(argv)
    text = json.dumps(tables(), indent=1, sort_keys=True)
    if args.json:
        args.json.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
