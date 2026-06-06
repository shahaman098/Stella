"""LEDGER web server — Flask UI for the money engine."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from flask import Flask, jsonify, render_template, request

from agent.pipeline import run, run_by_name

app = Flask(__name__)

CH_KEY = os.environ.get("COMPANIES_HOUSE_KEY", "")


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/lookup", methods=["POST"])
def lookup():
    data = request.json or {}
    query = (data.get("query") or "").strip()
    sector_override = (data.get("sector") or "").strip() or None

    if not query:
        return jsonify({"error": "Please enter a postcode or business name"}), 400

    # Detect postcode vs name
    import re
    is_postcode = bool(re.match(r"^[A-Z]{1,2}\d{1,2}[A-Z]?\s*\d[A-Z]{2}$", query, re.I))

    if is_postcode:
        result = run(query.upper())
    else:
        if not CH_KEY:
            return jsonify({"error": "Business name lookup requires COMPANIES_HOUSE_KEY — use a postcode instead"}), 400
        result = run_by_name(query, api_key=CH_KEY)

    # Apply sector override to first business if requested
    if sector_override and result.get("businesses"):
        from engines.rules_relief import Business, assess, _gross_bill
        from dataclasses import asdict
        b = result["businesses"][0]
        rv = b["rateable_value"]
        biz = Business(
            name=b["name"], rateable_value=rv, borough=b["borough"],
            sector=sector_override, uarn=b["uarn"], address=b["address"], postcode=b["postcode"]
        )
        findings = assess(biz)
        total = sum(f.annual_value for f in findings)
        back  = sum(f.backdated_value for f in findings)
        confs = [f.confidence for f in findings]
        highest = "high" if "high" in confs else ("medium" if "medium" in confs else ("low" if confs else "none"))
        b["sector"] = sector_override
        b["gross_annual_bill"] = round(_gross_bill(rv, sector_override), 2)
        b["findings"] = [asdict(f) for f in findings]
        b["totals"] = {"total_annual_savings": round(total, 2),
                       "total_backdated": round(back, 2), "highest_confidence": highest}

    return jsonify(result)


@app.route("/api/draft-email", methods=["POST"])
def draft_email():
    data = request.json or {}
    business = data.get("business", {})
    try:
        from agent.llm import chat
        finding_lines = "\n".join(
            f"- {f['headline']}: £{f['annual_value']:,.0f}/yr"
            for f in business.get("findings", [])
            if f.get("annual_value")
        )
        prompt = (
            f"Draft a short, professional email from a small business owner to their local "
            f"council claiming business rates relief. Use these details:\n"
            f"Business address: {business.get('address')}\n"
            f"UARN: {business.get('uarn')}\n"
            f"Borough: {business.get('borough')}\n"
            f"Rateable value: £{business.get('rateable_value', 0):,.0f}\n"
            f"Relief findings:\n{finding_lines}\n\n"
            f"Keep it under 150 words. Include the UARN. Be polite and direct. "
            f"Do NOT invent any figures — only use what's above."
        )
        email = chat(prompt, system="You are a professional letter-writing assistant for small businesses.")
        return jsonify({"email": email})
    except Exception as e:
        return jsonify({"error": f"LLM unavailable (is Ollama running?): {e}"}), 503


@app.route("/api/grants", methods=["POST"])
def grants():
    data = request.json or {}
    sector = data.get("sector", "other")
    borough = data.get("borough", "")
    try:
        from engines.rules_grants import match_grants
        matched = match_grants(sector=sector, borough=borough)
        return jsonify({"grants": matched})
    except ImportError:
        # Grants engine not yet built — return curated static list
        static = _static_grants(sector, borough)
        return jsonify({"grants": static})


def _static_grants(sector: str, borough: str) -> list[dict]:
    """Curated always-on grants for London small businesses."""
    grants = [
        {
            "name": "UK Shared Prosperity Fund — Small Business Support",
            "value": "Up to £25,000",
            "who": "London small businesses, especially in priority areas",
            "action": "Contact your borough council's economic development team",
            "url": "https://www.gov.uk/government/publications/uk-shared-prosperity-fund-prospectus",
            "confidence": "high",
        },
        {
            "name": "Start Up Loan (British Business Bank)",
            "value": "£500–£25,000 at 6% fixed",
            "who": "Businesses trading under 3 years",
            "action": "Apply at startuploans.co.uk",
            "url": "https://www.startuploans.co.uk/",
            "confidence": "high",
        },
        {
            "name": "GLA Good Growth Fund",
            "value": "£100k–£2M (community/cultural focus)",
            "who": "Businesses in regeneration areas, community benefit",
            "action": "Check current rounds at london.gov.uk/programmes-strategies/arts-culture/funding",
            "url": "https://www.london.gov.uk/programmes-strategies/arts-culture/funding",
            "confidence": "medium",
        },
        {
            "name": "London Growth Hub — Business Support",
            "value": "Free advice + matched funding referral",
            "who": "All London SMBs",
            "action": "Register at londongrowthub.co.uk",
            "url": "https://www.londongrowthub.co.uk/",
            "confidence": "high",
        },
    ]
    if sector in ("cafe", "pub", "hospitality", "retail"):
        grants.append({
            "name": "Hospitality & Retail Energy Efficiency Grant",
            "value": "Up to £5,000 (varies by borough)",
            "who": "Food & drink and retail businesses, energy efficiency works",
            "action": "Contact your borough council's sustainability team",
            "url": "https://www.find-government-grants.service.gov.uk/",
            "confidence": "medium",
        })
    if "hackney" in borough.lower() or "tower hamlets" in borough.lower() or "newham" in borough.lower():
        grants.append({
            "name": "East London Business Place Grant",
            "value": "Up to £10,000",
            "who": "East London SMBs — Hackney, Tower Hamlets, Newham priority",
            "action": "Contact ELBP directly",
            "url": "https://elbp.co.uk/",
            "confidence": "medium",
        })
    return grants


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"LEDGER running at http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=False)
