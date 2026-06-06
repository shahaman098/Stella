#!/usr/bin/env python3
"""Run LEDGER locally (Mac via tunnel) or on the Spark."""

import argparse
import json
import sys

from agent.pipeline import run


def main() -> int:
    parser = argparse.ArgumentParser(description="LEDGER — what your business is owed")
    parser.add_argument("business", help="Business name")
    parser.add_argument("postcode", help="London postcode, e.g. E8 1DY")
    parser.add_argument("--rv", type=float, help="Rateable value (£) for demo relief calc")
    args = parser.parse_args()

    result = run(args.business, args.postcode, rateable_value=args.rv)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
