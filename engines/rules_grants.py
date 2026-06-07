"""Grant eligibility engine — properly tailored to each business.

Rules:
- Only show a grant if there's a GENUINE specific reason for this business
- Generic "available to everyone" grants are shown with actual company data in reasons
- Ineligible grants are never shown
- match_reasons always reference actual company data (age, SIC, borough, RV)
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Literal

Eligibility = Literal["eligible", "likely", "check"]


@dataclass
class GrantMatch:
    name: str
    funder: str
    value: str
    eligibility: Eligibility
    match_reasons: list[str]
    blockers: list[str]
    action: str
    url: str
    deadline: str = "Rolling"


# ── SIC helpers ───────────────────────────────────────────────────────────────

def _sic_in(codes: list[str], *prefixes: str) -> bool:
    for c in codes:
        num = c.split()[0].strip()
        if any(num.startswith(p) for p in prefixes):
            return True
    return False

def _is_tech(c):        return _sic_in(c, "62","63","26","27","72","58")
def _is_creative(c):    return _sic_in(c, "59","60","90","91","74","73")
def _is_mfg(c):         return _sic_in(c, "10","11","12","13","14","15","16","17","18","20","21","22","23","24","25","26","27","28","29","30","31","32","33")
def _is_food(c):        return _sic_in(c, "561","562","563","101","102","103","104","105","106","107","108","110")
def _is_retail(c):      return _sic_in(c, "47","46")
def _is_health(c):      return _sic_in(c, "86","87","88","75")
def _is_construction(c):return _sic_in(c, "41","42","43")
def _is_professional(c):return _sic_in(c, "69","70","71","74","78")
def _is_rd(c):          return _sic_in(c, "72","71","20","21","26")

_EAST_LONDON = {"hackney","tower hamlets","newham","waltham forest","barking and dagenham","redbridge","havering","lewisham","greenwich"}
_OUTER_LONDON = {"barnet","bexley","bromley","croydon","ealing","enfield","harrow","havering","hillingdon","hounslow","kingston upon thames","merton","redbridge","richmond upon thames","sutton","waltham forest","barking and dagenham"}
_DEPRIVED = {"hackney","tower hamlets","newham","barking and dagenham","haringey","waltham forest","lewisham","southwark","lambeth","islington"}

def _east(b):     return b.lower() in _EAST_LONDON
def _outer(b):    return b.lower() in _OUTER_LONDON
def _deprived(b): return b.lower() in _DEPRIVED


def match_grants(
    sector: str,
    sic_codes: list[str] | None = None,
    borough: str = "",
    rateable_value: float = 0.0,
    company_age_years: float | None = None,
    company_type: str = "",
    company_name: str = "",
) -> list[dict]:
    sic  = sic_codes or []
    age  = company_age_years
    b    = borough.strip().lower()
    rv   = rateable_value
    s    = sector.lower()
    name = company_name
    results: list[GrantMatch] = []

    # ── 1. Start Up Loan ─────────────────────────────────────────────────────
    # Only show if business is ≤ 5 years old or age unknown
    if age is None or age <= 5:
        reasons = []
        blockers = []
        if age is not None and age <= 2:
            reasons.append(f"{name or 'Your business'} is {age:.0f} year(s) old well within the startup window")
            elig = "eligible"
        elif age is not None and age <= 5:
            reasons.append(f"At {age:.0f} years old you may still qualify (British Business Bank considers trading history)")
            elig = "likely"
        else:
            reasons.append("Age unconfirmed (worth checking eligibility directly)")
            elig = "check"
        if rv > 0 and rv < 51000:
            reasons.append(f"RV £{rv:,.0f} confirms small business scale")
        results.append(GrantMatch(
            name="Start Up Loan (British Business Bank)",
            funder="British Business Bank / UK Gov",
            value="£500–£25,000 at 6% fixed + 12 months free mentoring",
            eligibility=elig,
            match_reasons=reasons, blockers=blockers,
            action="Apply at startuploans.co.uk, decision in ~4 weeks",
            url="https://www.startuploans.co.uk/",
        ))

    # ── 2. UKSPF — only show with specific borough or sector angle ───────────
    ukspf_reasons = []
    ukspf_elig = None
    if _deprived(b):
        ukspf_reasons.append(f"{borough} is a UKSPF priority borough (higher allocation)")
        ukspf_elig = "eligible"
    if _outer(b) and not ukspf_reasons:
        ukspf_reasons.append(f"{borough} is an outer London priority area for UKSPF business support")
        ukspf_elig = "likely"
    if s in ("cafe","pub","hospitality","retail","leisure") and rv < 51000:
        ukspf_reasons.append(f"{s.title()} sector is a UKSPF high street recovery priority")
        if not ukspf_elig: ukspf_elig = "likely"
    if rv > 0 and rv < 15000:
        ukspf_reasons.append(f"RV £{rv:,.0f} (micro business scale, UKSPF primary target)")
        if not ukspf_elig: ukspf_elig = "likely"
    if ukspf_reasons:
        results.append(GrantMatch(
            name="UK Shared Prosperity Fund",
            funder="HM Government via London Borough Councils",
            value="Up to £25,000 (varies by borough)",
            eligibility=ukspf_elig,
            match_reasons=ukspf_reasons, blockers=[],
            action=f"Contact {borough or 'your'} Council economic development team",
            url="https://www.gov.uk/government/publications/uk-shared-prosperity-fund-prospectus",
            deadline="Rolling (borough-dependent)",
        ))

    # ── 3. London Growth Hub — show for all but with specific reasons ─────────
    lgh_reasons = [f"{name or 'Your business'} qualifies as a London SME with < 250 employees"]
    if rv > 0 and rv < 51000:
        lgh_reasons.append(f"RV £{rv:,.0f} confirms SME scale (advisers will match further grants)")
    if age and age > 2:
        lgh_reasons.append(f"At {age:.0f} years trading, growth advisory is the most relevant entry point")
    results.append(GrantMatch(
        name="London Growth Hub: Free Advice + Grant Referral",
        funder="GLA / Mayor of London",
        value="Free diagnostics + matched grant referral (£10k–£100k+)",
        eligibility="eligible",
        match_reasons=lgh_reasons, blockers=[],
        action="Register at londongrowthub.co.uk (free, no commitment)",
        url="https://www.londongrowthub.co.uk/",
    ))

    # ── 4. Innovate UK — only for tech, R&D, or manufacturing ────────────────
    if _is_tech(sic) or _is_rd(sic) or _is_mfg(sic):
        ik_reasons = []
        if _is_tech(sic):    ik_reasons.append(f"SIC codes confirm tech/digital sector (core Innovate UK target)")
        if _is_rd(sic):      ik_reasons.append("R&D SIC codes confirmed. Directly eligible for innovation funding.")
        if _is_mfg(sic):     ik_reasons.append("Manufacturing sector. Eligible for product/process innovation grants.")
        elig = "likely" if (_is_tech(sic) or _is_rd(sic)) else "check"
        results.append(GrantMatch(
            name="Innovate UK Smart Grants",
            funder="UK Research & Innovation (UKRI)",
            value="£25,000–£500,000 (25%–100% match funded)",
            eligibility=elig,
            match_reasons=ik_reasons,
            blockers=["Must demonstrate innovation beyond existing technology"],
            action="Check open rounds at apply-for-innovation-funding.service.gov.uk",
            url="https://apply-for-innovation-funding.service.gov.uk/",
            deadline="Competitive rounds (quarterly)",
        ))

    # ── 5. R&D Tax Credits — only for companies likely doing R&D ─────────────
    if _is_tech(sic) or _is_rd(sic) or _is_mfg(sic) or _is_health(sic):
        rd_reasons = []
        blockers   = []
        if _is_tech(sic):    rd_reasons.append("Tech/software development likely qualifies as R&D")
        if _is_rd(sic):      rd_reasons.append(f"SIC code confirms research & development activity")
        if _is_mfg(sic):     rd_reasons.append("Manufacturing process improvement often qualifies as R&D")
        if _is_health(sic):  rd_reasons.append("Healthcare/science sector. Clinical R&D typically qualifies.")
        rd_reasons.append("If you've built anything new or solved a technical problem, R&D credits likely apply")
        if company_type.lower() not in ("ltd","plc","limited","private limited company",""):
            blockers.append(f"Company type '{company_type}' (must be Ltd/PLC to claim)")
        results.append(GrantMatch(
            name="R&D Tax Credits (HMRC)",
            funder="HMRC",
            value="Up to 33p per £1 spent on R&D",
            eligibility="likely" if not blockers else "check",
            match_reasons=rd_reasons, blockers=blockers,
            action="Claim via Corporation Tax return — specialist accountant recommended",
            url="https://www.gov.uk/guidance/corporation-tax-research-and-development-rd-relief",
            deadline="2 years after accounting period end",
        ))

    # ── 6. GLA Good Growth Fund — creative, cultural, east/deprived areas ────
    gg_reasons = []
    gg_elig    = None
    if _is_creative(sic):
        gg_reasons.append("Creative/cultural sector is a primary GLA Good Growth Fund target")
        gg_elig = "likely"
    if _east(b) or _deprived(b):
        gg_reasons.append(f"{borough} is a GLA priority area for inclusive growth investment")
        gg_elig = "eligible" if gg_elig == "likely" else "likely"
    if s in ("leisure","hospitality") and _deprived(b):
        gg_reasons.append(f"Community leisure/hospitality in {borough} — strong fit for Good Growth criteria")
        if not gg_elig: gg_elig = "likely"
    if gg_reasons:
        results.append(GrantMatch(
            name="GLA Good Growth Fund",
            funder="Greater London Authority (Mayor of London)",
            value="£100,000–£2,000,000",
            eligibility=gg_elig,
            match_reasons=gg_reasons,
            blockers=["Must demonstrate community/cultural benefit — not purely commercial"],
            action="Check open rounds at london.gov.uk/good-growth-fund",
            url="https://www.london.gov.uk/programmes-strategies/arts-culture/funding",
            deadline="Competitive — check for open rounds",
        ))

    # ── 7. Hospitality Energy Grant — F&B and hospitality ONLY ───────────────
    if s in ("cafe","pub","hospitality") or _is_food(sic):
        energy_reasons = [f"{s.title()} sector is the explicit target of this energy grant"]
        if s == "cafe":      energy_reasons.append("High energy use in espresso machines, refrigeration, and cooking")
        elif s == "pub":     energy_reasons.append("Draught systems, cellar cooling, and kitchen energy costs qualify")
        elif s == "hospitality": energy_reasons.append("Commercial kitchen and HVAC costs are primary qualifying expenses")
        if rv < 51000:
            energy_reasons.append(f"RV £{rv:,.0f} — small venue scale, typical target for this scheme")
        results.append(GrantMatch(
            name="Hospitality Sector Energy Efficiency Grant",
            funder="London boroughs + DESNZ",
            value="Up to £5,000 (varies by borough)",
            eligibility="likely",
            match_reasons=energy_reasons,
            blockers=["Borough-specific — availability varies, check your council"],
            action=f"Contact {borough or 'your'} borough council sustainability team",
            url="https://www.find-government-grants.service.gov.uk/",
        ))

    # ── 8. East London Business Place — East London ONLY ─────────────────────
    if _east(b):
        results.append(GrantMatch(
            name="East London Business Place (ELBP) Grant",
            funder="ELBP / GLA",
            value="Up to £10,000 + free mentoring",
            eligibility="eligible",
            match_reasons=[
                f"{borough} is within ELBP's priority catchment area",
                "Direct grant for local SMEs — no match funding required",
                f"{name or 'Your business'} qualifies based on location alone",
            ],
            blockers=[],
            action="Apply directly at elbp.co.uk",
            url="https://elbp.co.uk/",
        ))

    # ── 9. Creative Enterprise Programme — creative sector ONLY ─────────────
    if _is_creative(sic) or s == "leisure":
        results.append(GrantMatch(
            name="Creative Enterprise Programme",
            funder="Arts Council England + GLA",
            value="£2,500–£15,000 + free business support",
            eligibility="likely",
            match_reasons=[
                "Creative/cultural SIC codes confirmed" if _is_creative(sic) else f"{s.title()} sector with cultural dimension",
                "Programme specifically targets London creative SMEs",
            ],
            blockers=["Must have cultural/creative mission — not purely commercial"],
            action="Check artscouncil.org.uk for open rounds",
            url="https://www.artscouncil.org.uk/funding",
            deadline="Competitive rounds",
        ))

    # ── 10. Made Smarter — manufacturing/industrial ONLY ─────────────────────
    if _is_mfg(sic) or s == "industrial":
        results.append(GrantMatch(
            name="Made Smarter — Digital Adoption Grant",
            funder="Department for Business and Trade",
            value="Up to £20,000 (50% match) + free digital audit",
            eligibility="likely",
            match_reasons=[
                "Manufacturing/industrial sector is the sole target of this programme",
                "Grant covers industrial IoT, automation, and digital manufacturing tools",
                f"RV £{rv:,.0f} confirms SME manufacturing scale" if rv > 0 else "SME scale qualifies",
            ],
            blockers=["Must have manufacturing operations in England"],
            action="Apply via madesmarter.uk/apply",
            url="https://www.madesmarter.uk/",
        ))

    # ── 11. Retail High Streets — retail in deprived/outer areas ─────────────
    if (_is_retail(sic) or s == "retail") and (_deprived(b) or _outer(b)):
        results.append(GrantMatch(
            name="High Streets Heritage Action Zone Grant",
            funder="Historic England + Local Authority",
            value="£5,000–£50,000 for shopfront/building improvements",
            eligibility="likely" if _deprived(b) else "check",
            match_reasons=[
                f"Retail business in {borough} — priority area for High Streets programme",
                "Covers shopfront improvements, signage, accessibility works",
            ],
            blockers=["Property must be in a designated Heritage Action Zone — check with your council"],
            action=f"Contact {borough} Council planning/regeneration team",
            url="https://historicengland.org.uk/services-skills/heritage-action-zones/",
        ))

    # ── 12. Net Zero — all businesses but with specific reasons ──────────────
    nz_reasons = []
    if s in ("cafe","pub","hospitality","industrial","retail"):
        nz_reasons.append(f"{s.title()} sector has high energy costs — free audit identifies savings")
    if rv > 0:
        nz_reasons.append(f"Business premises at RV £{rv:,.0f} qualifies for commercial energy support")
    if b:
        nz_reasons.append(f"{borough} Council has a local net zero business programme")
    results.append(GrantMatch(
        name="Net Zero Business Energy Support",
        funder="DESNZ / local energy hubs",
        value="Free energy audit + up to £5,000 for efficiency works",
        eligibility="check",
        match_reasons=nz_reasons or ["Available to all London SMEs"],
        blockers=["Varies by borough — contact your local energy hub"],
        action="Check businessclimatesupport.co.uk or your borough council",
        url="https://www.businessclimatesupport.co.uk/",
    ))

    # ── Sort and return ───────────────────────────────────────────────────────
    order = {"eligible": 0, "likely": 1, "check": 2}
    results.sort(key=lambda g: order[g.eligibility])
    return [
        {
            "name":          g.name,
            "funder":        g.funder,
            "value":         g.value,
            "eligibility":   g.eligibility,
            "match_reasons": g.match_reasons,
            "blockers":      g.blockers,
            "action":        g.action,
            "url":           g.url,
            "deadline":      g.deadline,
        }
        for g in results
    ]
