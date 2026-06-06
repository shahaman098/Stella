"""Verify a real business against the VOA index and print the relief findings.

Usage:
    python3 data/verify_business.py E8 1DY
    python3 data/verify_business.py "E8 1DY" --name "Artisan Cafe"
    python3 data/verify_business.py "E8 1DY" --rv 11500 --sector cafe

Cross-check RV at: https://www.gov.uk/correct-your-business-rates
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.pipeline import run, _lookup_postcode
from engines.rules_relief import Business, assess, _gross_bill


def main() -> None:
    parser = argparse.ArgumentParser(description="LEDGER — verify a real business end-to-end")
    parser.add_argument("postcode", nargs="+", help="Postcode (space ok: E8 1DY)")
    parser.add_argument("--rv",     type=float, help="Override rateable value")
    parser.add_argument("--sector", help="Override sector: cafe/retail/pub/hospitality/office/industrial/leisure/other")
    parser.add_argument("--name",   default="", help="Business name for display")
    args = parser.parse_args()

    postcode = " ".join(args.postcode)

    print(f"\n{'='*60}")
    print("LEDGER — Verification Report")
    print(f"Postcode : {postcode}")
    if args.name:
        print(f"Business : {args.name}")
    print(f"{'='*60}\n")

    matches = _lookup_postcode(postcode)
    if not matches:
        print(f"WARNING: No VOA entries found for {postcode}")
        print("  Check: https://www.gov.uk/correct-your-business-rates")
        if not args.rv:
            print("  Pass --rv <value> to run a manual check")
            sys.exit(1)
    else:
        print(f"Found {len(matches)} VOA entry/entries:")
        for m in matches:
            print(f"  UARN        : {m['uarn']}")
            print(f"  Description : {m['desc_text']}")
            print(f"  Sector      : {m['sector']}  (auto-classified — override with --sector if wrong)")
            print(f"  RV          : £{m['rateable_value']:,.0f}")
            print(f"  Address     : {m['address']}")
            print()

    rv     = args.rv or (matches[0]["rateable_value"] if matches else None)
    sector = args.sector or (matches[0]["sector"] if matches else "other")
    borough = matches[0]["borough"] if matches else "Unknown"

    if rv is None:
        print("No RV available — pass --rv")
        sys.exit(1)

    print(f"Running engine: RV=£{rv:,.0f}  sector={sector}  borough={borough}")
    biz = Business(name=args.name or "Business", rateable_value=rv, borough=borough, sector=sector)
    findings = assess(biz)
    gross = _gross_bill(rv, sector)
    print(f"  Gross annual bill (before relief) : £{gross:,.0f}\n")

    if not findings:
        print("  No relief findings — business pays full gross bill.")
    for f in findings:
        print(f"  ✓ {f.headline}")
        if f.annual_value:
            print(f"    Annual saving  : £{f.annual_value:,.0f}/yr")
        if f.backdated_value:
            print(f"    Backdated est. : £{f.backdated_value:,.0f}")
        print(f"    Confidence     : {f.confidence}")
        print(f"    Action         : {f.action}")
        print(f"    Source         : {f.source}")
        print()

    total = sum(f.annual_value for f in findings)
    back  = sum(f.backdated_value for f in findings)
    print(f"{'─'*40}")
    print(f"TOTAL ANNUAL SAVING : £{total:,.0f}/yr")
    print(f"TOTAL BACKDATED     : £{back:,.0f}")
    print()
    print("CROSS-CHECK:")
    print("  1. Confirm RV at https://www.gov.uk/correct-your-business-rates")
    print("  2. Parsed RV must match the official figure")
    print("  3. Confirm sector matches property use (wrong sector → wrong multiplier)")
    print("  4. Check real bill ≈ gross_annual_bill (within £20)")


if __name__ == "__main__":
    main()
