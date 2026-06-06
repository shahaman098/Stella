"""End-to-end spine: business input → structured finding → plain-English brief."""

from __future__ import annotations

from agent.llm import chat

SYSTEM = (
    "You are LEDGER, an on-device agent for London small businesses. "
    "You explain business rates relief and grants in plain English. "
    "Never invent pound figures — only explain what the structured data says."
)


def run(business_name: str, postcode: str, rateable_value: float | None = None) -> dict:
    """Demo path until VOA ingest is wired. Pass RV manually for now."""
    finding = {
        "business": business_name,
        "postcode": postcode,
        "rateable_value": rateable_value,
        "status": "demo",
        "note": "VOA ingest not yet connected — using manual RV if provided",
    }

    if rateable_value is not None and rateable_value <= 12000:
        finding["relief"] = {
            "scheme": "Small Business Rate Relief",
            "entitlement_pct": 100,
            "summary": f"RV £{rateable_value:,.0f} is at or below £12,000 — likely full SBRR",
        }
    elif rateable_value is not None and rateable_value < 15000:
        finding["relief"] = {
            "scheme": "Small Business Rate Relief (tapered)",
            "summary": f"RV £{rateable_value:,.0f} is in the SBRR taper band",
        }
    elif rateable_value is not None:
        finding["relief"] = {
            "scheme": "SBRR challenge wedge",
            "summary": f"RV £{rateable_value:,.0f} is above £15,000 — check 2026 revaluation challenge",
        }

    explanation = chat(
        f"Business: {business_name}\nPostcode: {postcode}\n"
        f"Structured finding JSON:\n{finding}\n\n"
        "Write a 3-sentence plain-English brief for the owner. "
        "If relief data is present, lead with the money opportunity.",
        system=SYSTEM,
    )
    finding["brief"] = explanation
    return finding
