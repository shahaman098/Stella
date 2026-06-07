# STELLA — Unclaimed Business Money Engine

> On-device AI agent that finds and claims unclaimed government money for London SMBs.
> Built on NVIDIA DGX. Every £ figure traces to a statutory source. Zero internet required.

---

## The Problem

**£317,000,000** in Small Business Rate Relief goes unclaimed in London every year.

141,248 commercial properties qualify. The government does not tell them. Councils do not apply it automatically. Most owners have never heard of it. Backdated to April 2023 (the start of the current rating list), the total unclaimed value across London is **£950,731,945**.

A single café at RV £8,500 in Camden is owed:
- £3,247/yr in SBRR
- £9,741 backdated to April 2023
- Potentially £15,000+ in additional grants

STELLA finds this in under 10 seconds and produces the claim letter.

---

## What STELLA Does

### Street Scanner
Enter any London postcode. STELLA scans every commercial property at that address against the 2026 VOA rating list, computes SBRR eligibility using 2026/27 statutory multipliers, and returns exact annual savings, backdated lump sums, and confidence ratings — all traceable to gov.uk rules.

### My Business
Enter a business name and postcode. STELLA:
1. Verifies the company against 5,607,936 Companies House records
2. Matches it to the exact VOA property entry
3. Computes SBRR eligibility and annual saving
4. Generates an 8-card eligibility tracker (SBRR status, total money on table, backdating urgency, RV cliff warning, location bonuses, sector peer comparison, postcode peers, London-wide context)
5. Matches grants from 12 programmes based on actual SIC codes, borough, company age, and RV
6. Streams a ready-to-send claim letter via local Nemotron LLM

### Priority Scanner
Select a London borough. STELLA scans all eligible properties in that borough, cross-matches the Companies House database to identify the actual business at each address, and ranks the top 50 by unclaimed annual value — enabling targeted SMB outreach at scale.

### AI Grant Applications
For every matched grant, STELLA streams a complete application package:
- Section 1: Why this specific business qualifies (using actual SIC codes, RV, borough, age)
- Section 2: Professional application email, under 120 words, ready to send
- Section 3: Documents checklist with 5 specific items to gather
- Section 4: Step-by-step how to apply with URLs and deadlines

All streamed word-by-word via Nemotron on DGX. No data leaves the local network.

---

## Numbers

| Metric | Value |
|---|---|
| London commercial properties (VOA 2026) | 311,750 |
| 100% SBRR eligible (RV ≤ £12,000) | 117,188 |
| Tapered SBRR eligible (RV £12k–£15k) | 24,060 |
| Annual unclaimed SBRR across London | £316,910,648 |
| Backdated value (3 years from April 2023) | £950,731,945 |
| Companies House records indexed | 5,607,936 |
| London boroughs with direct council contacts | 33 |
| Grant programmes matched | 12 |

**Top boroughs by eligible properties:**
Tower Hamlets (10,636) · Westminster (9,216) · City of London (7,581) · Camden (6,555) · Southwark (5,608)

---

## Architecture

```
                        ┌──────────────────────────────┐
                        │         Browser / UI          │
                        │   server/templates/index.html │
                        │                               │
                        │  Street Scanner  My Business  │
                        │  Priority List   Grant Drafter│
                        └─────────────┬────────────────┘
                                      │ REST + SSE
                        ┌─────────────▼────────────────┐
                        │       Flask Server            │
                        │       server/app.py           │
                        │                               │
                        │  /api/biz-profile             │
                        │  /api/lookup                  │
                        │  /api/insights                │
                        │  /api/priority-scan           │
                        │  /api/grant-application (SSE) │
                        │  /api/draft-email      (SSE)  │
                        └──┬──────┬────────┬────────────┘
                           │      │        │
             ┌─────────────▼──┐ ┌─▼──────┐ ┌▼─────────────────────┐
             │  Data Layer    │ │ Engine │ │   LLM Layer           │
             │                │ │ Layer  │ │                       │
             │ VOA CSV 311k   │ │        │ │  agent/llm.py         │
             │ CH SQLite 5.6M │ │ rules_ │ │                       │
             │ Borough        │ │ relief │ │  Primary:             │
             │ Contacts 33    │ │        │ │  DGX Spark            │
             │ borough_       │ │ rules_ │ │  10.18.216.24:30000   │
             │ contacts.py    │ │ grants │ │  Nemotron (reasoning) │
             └────────────────┘ └────────┘ │                       │
                                           │  Fallback:            │
                                           │  Ollama localhost     │
                                           │  llama3.2             │
                                           └───────────────────────┘
```

### Stack

| Layer | Technology |
|---|---|
| Web server | Python 3.10 + Flask 3.1 |
| UI | Vanilla JS, single HTML file, dark theme |
| LLM | Nemotron on NVIDIA DGX Spark (OpenAI-compatible API) |
| LLM fallback | Ollama / llama3.2 (local laptop) |
| Company data | SQLite 3 with FTS5 full-text search |
| Property data | CSV scan (311k rows, ~40ms per postcode lookup) |
| Streaming | Server-Sent Events (SSE) via Flask stream_with_context |
| Deployment | Local network only — no cloud, no external API calls |

---

## Data Sources

### VOA 2026 Rating List (`data/voa_london_index.csv`)
- **Source:** Valuation Office Agency open data — 2026 revaluation
- **Size:** 41MB, 311,750 records, committed to repo
- **Fields:** UARN · borough · address · postcode · sector · rateable value · SCAT code · composite flag · description code
- **Sectors classified:** retail · office · cafe · pub · hospitality · leisure · industrial · other
- **Update cycle:** Every revaluation (~3 years). Next: April 2029

### Companies House Bulk Register (`data/ch_index.db`)
- **Source:** companieshouse.gov.uk/about/dataProducts — `BasicCompanyDataAsOneFile`
- **Size:** 1.2GB SQLite, 5,607,936 companies — all with postcodes and SIC codes
- **Indexes:** FTS5 on company name (prefix search, sub-50ms), B-tree on postcode, primary key on company number
- **Fields:** company_number · name · postcode · status · date_of_creation · sic1–sic4
- **Update cycle:** Monthly. Current build: June 2026

### Borough Contacts (`data/borough_contacts.py`)
- 33 London boroughs + City of London
- Direct business rates team email and phone per borough
- SBRR application URL per council (with gov.uk fallback for councils that 403 bots)

### Statutory Rules
| Rule | Source |
|---|---|
| 2026/27 multipliers | gov.uk notification 2/2026 |
| SBRR eligibility | gov.uk/apply-for-business-rate-relief |
| Pub/live-music relief | gov.uk publication 1/2026 |
| SSB 2026 transitional | gov.uk SSB LA guidance 2026 |
| Backdating | Rating List start April 2023 |

---

## Relief Engine (`engines/rules_relief.py`)

Deterministic Python. The LLM never touches these calculations.

**2026/27 Multipliers:**

| Property type | Multiplier |
|---|---|
| Small business, RHL sectors (retail/cafe/pub/hospitality/leisure) | 0.382p per £1 RV |
| Small business, non-RHL | 0.432p per £1 RV |
| Standard, RHL (RV £51k–£499k) | 0.430p per £1 RV |
| Standard, non-RHL | 0.480p per £1 RV |
| High value (RV ≥ £500k) | 0.508p per £1 RV |

**SBRR Rules:**
- RV ≤ £12,000 → 100% relief (zero rates bill)
- RV £12,001–£15,000 → tapered: 1% reduction per £30 above £12,000
- RV > £15,000 → no SBRR
- Multi-property disqualification: any second property with RV ≥ £2,900 removes eligibility (12-month grace on acquisition)

**Backdating:**
Conservative estimate: 3 years from April 2023. Councils may backdate further — STELLA always instructs the user to ask. Statutory maximum: 6 years.

---

## Grants Engine (`engines/rules_grants.py`)

12 grant programmes. Each has genuine eligibility gates — not shown to everyone.

| Grant | Eligibility Gate | Value |
|---|---|---|
| Start Up Loan | Company age ≤ 5 years | £500–£25,000 at 6% |
| UK Shared Prosperity Fund | Deprived/outer borough OR high-street sector | Up to £25,000 |
| London Growth Hub | All London SMEs | Free advisory + referral |
| Innovate UK Smart Grants | Tech/R&D/manufacturing SIC codes only | £25k–£500k |
| R&D Tax Credits | Tech/manufacturing/health SIC codes only | Up to 33p per £1 |
| GLA Good Growth Fund | Creative sector OR east/deprived borough | £100k–£2M |
| Hospitality Energy Grant | Cafe/pub/food SIC codes only | Up to £5,000 |
| East London Business Place | East London boroughs only | Up to £10,000 |
| Creative Enterprise | Creative/cultural SIC codes only | £2,500–£15,000 |
| Made Smarter | Manufacturing SIC codes only | Up to £20,000 |
| High Streets Heritage | Retail in deprived/outer areas | £5k–£50,000 |
| Net Zero Support | All businesses with sector-specific reasoning | Free audit + £5,000 |

**SIC code classification example:**
A café (SIC 56210) sees: London Growth Hub, UKSPF, Hospitality Energy, Net Zero.
A tech startup (SIC 72110) in Hackney sees: Start Up Loan, UKSPF, London Growth Hub, Innovate UK, R&D Tax Credits, GLA Good Growth, ELBP, Net Zero.

Every `match_reason` references actual company data — name, RV, borough, SIC code, age. No generic filler.

---

## LLM Layer (`agent/llm.py`)

```
Request → DGX Spark (Nemotron) → SSE stream → browser
              │ if fails
              └─→ Ollama (llama3.2) → SSE stream → browser
```

**Why Nemotron requires `max_tokens: 4096`:**
Nemotron is a reasoning model. It uses tokens for chain-of-thought before writing its answer. With fewer tokens it exhausts the budget during thinking and returns empty `content`. 4096 is the minimum for reliable outputs.

**Streaming wire format:**
```
data: {"t": "Hello"}\n\n
data: {"t": ", this"}\n\n
data: {"t": " is streamed"}\n\n
data: [DONE]\n\n
```

Flask endpoint pattern:
```python
def generate():
    for chunk in stream_chat(prompt):
        yield f"data: {json.dumps({'t': chunk})}\n\n"
    yield "data: [DONE]\n\n"

return Response(stream_with_context(generate()),
    mimetype="text/event-stream",
    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
```

---

## Eligibility Tracker (`/api/insights`)

8 insight cards returned for every My Business lookup, sorted by priority:

| Priority | Card Type | Trigger |
|---|---|---|
| 1 | SBRR Status | Always — ELIGIBLE / TAPERED / NOT ELIGIBLE |
| 2 | Total Money on Table | Always — SBRR + grant count combined |
| 3 | Backdating Urgency | RV ≤ £15,000 — specific £ figure + April 2023 deadline |
| 4 | RV Cliff Warning | RV within £1,500 of £12k or £15k threshold |
| 5 | Location Bonus | East/deprived boroughs (ELBP, UKSPF priority, GLA Good Growth) |
| 6 | Sector Peer Comparison | RV vs median of all same-sector businesses in same borough |
| 7 | Postcode Peers | Other businesses at same postcode, their RVs and eligibility |
| 8 | London Context | 117k eligible, £317M/yr, why you must apply (not automatic) |

---

## API Reference

### `POST /api/biz-profile`
My Business: name + postcode → full analysis.

**Request:**
```json
{ "name": "Prufrock Coffee", "postcode": "EC1N 7TE" }
```

**Response (abbreviated):**
```json
{
  "biz_name": "Prufrock Coffee",
  "ch_verification": "likely",
  "ch_profile": { "name": "...", "number": "...", "status": "Active" },
  "sic_codes": ["56210 - Licensed restaurants"],
  "company_age_years": 16,
  "property": {
    "borough": "Camden",
    "sector": "cafe",
    "rateable_value": 11000.0,
    "totals": { "total_annual_savings": 4202.0, "total_backdated": 12606.0 }
  },
  "grants": [
    { "name": "London Growth Hub...", "eligibility": "eligible", "match_reasons": [...] }
  ],
  "council": { "email": "businessrates@camden.gov.uk", "phone": "020 7974 6019" }
}
```

### `POST /api/lookup`
Street Scanner: postcode → all properties.

```json
{ "query": "WC2H 7NA" }
```

### `POST /api/insights`
Eligibility tracker cards.

```json
{
  "rateable_value": 8500, "sector": "cafe", "borough": "Camden",
  "postcode": "WC2H 7NA", "biz_name": "Prufrock Coffee",
  "grants": [...], "sbrr_saving": 3247
}
```

### `POST /api/priority-scan`
Borough scan for unclaimed money.

```json
{ "borough": "Camden", "limit": 20 }
```

### `POST /api/grant-application` — SSE
Full 4-section application package, streamed.

```json
{ "grant": { ...grantObject }, "business": { ...bizObject } }
```

### `POST /api/draft-email` — SSE
Quick claim email or action steps.

```json
{ "grant": {...}, "business": {...}, "mode": "email" }
```

---

## Setup

### Requirements
- Python 3.10+
- Flask (`pip install flask`)
- DGX Spark at `http://10.18.216.24:30000` (or Ollama locally as fallback)
- `data/ch_index.db` — see build instructions below
- `data/voa_london_index.csv` — included in this repo

### Run

```bash
git clone https://github.com/shahaman098/Stella
cd Stella
pip install flask

# Optional: set CH API key for higher-confidence company verification
export COMPANIES_HOUSE_KEY=your_key_here

# Start (default port 5001)
python3 server/app.py

# Custom port, exposed on network
PORT=5000 python3 server/app.py
```

Open `http://localhost:5001`

### Build the Companies House Index

One-time setup, ~25 minutes. Not required — falls back to CH live API if `COMPANIES_HOUSE_KEY` is set.

```bash
# Download bulk data (~500MB ZIP, free, no login)
curl -O "https://download.companieshouse.gov.uk/BasicCompanyDataAsOneFile-2026-06-01.zip"
unzip BasicCompanyDataAsOneFile*.zip -d data/ch_raw/

# Ingest into SQLite (builds data/ch_index.db, ~1.2GB)
python3 data/ingest_companies_local.py

# Verify
python3 -c "
import sqlite3
c = sqlite3.connect('data/ch_index.db').cursor()
c.execute('SELECT COUNT(*) FROM companies')
print(c.fetchone()[0], 'companies indexed')
"
# 5607936 companies indexed
```

### Deploy to DGX (full offline)

```bash
# On DGX — clone and build
git clone https://github.com/shahaman098/Stella && cd Stella
pip install flask

# Copy CH index from your machine (or rebuild above)
scp your-machine:~/NVIDIAHack/Stella/data/ch_index.db data/

# No internet needed after this point
# DGX_URL defaults to http://10.18.216.24:30000
python3 server/app.py
```

### Environment Variables

| Variable | Default | Description |
|---|---|---|
| `PORT` | `5001` | Flask server port |
| `COMPANIES_HOUSE_KEY` | _(empty)_ | CH live API key. Offline mode if unset. |
| `DGX_URL` | `http://10.18.216.24:30000` | LLM endpoint (OpenAI-compatible) |
| `DGX_MODEL` | `nemotron` | Model name on DGX |
| `OLLAMA_URL` | `http://localhost:11434` | Ollama fallback URL |
| `OLLAMA_MODEL` | `llama3.2` | Ollama fallback model |

---

## Project Structure

```
Stella/
├── server/
│   ├── app.py                     # Flask server + all API routes
│   └── templates/
│       └── index.html             # Single-page UI (Street Scanner, My Business, Priority List)
│
├── engines/
│   ├── rules_relief.py            # SBRR + rates calculation (deterministic, LLM-free)
│   └── rules_grants.py            # Grant eligibility matching (SIC-gated)
│
├── agent/
│   ├── llm.py                     # DGX/Ollama streaming client
│   └── pipeline.py                # Postcode-to-findings pipeline + JSON contract
│
├── data/
│   ├── voa_london_index.csv       # 311,750 VOA properties (in repo)
│   ├── ch_index.db                # 5.6M Companies House records (local only, gitignored)
│   ├── borough_contacts.py        # 33 borough business rates team contacts
│   ├── ingest_companies_local.py  # CH bulk CSV → SQLite + FTS5 search
│   ├── ingest_companies.py        # CH live API client
│   └── ingest_voa.py              # VOA raw data → indexed CSV
│
├── tests/
│   └── test_rules_relief.py       # Deterministic rule regression tests
│
├── run.py                         # CLI interface
├── DATASETS.md                    # Full data provenance and rebuild instructions
└── README.md
```

---

## Design Principles

**LLM never touches the numbers.**
All £ figures come from the deterministic relief engine. The LLM only writes prose — emails, narratives, application text. Every saving, backdated amount, and eligibility verdict is traceable to a published statutory source without any AI involvement.

**Offline first.**
Core functionality works with zero internet. VOA data is in the repo. CH data is local SQLite. The LLM runs on DGX over the local network. The CH live API is an optional enhancement for company verification confidence — not a dependency.

**Tailored, not generic.**
Grants are only shown when there is a specific reason for that business. R&D Tax Credits never appear for a café. ELBP never appears for a Westminster office. Match reasons always reference the actual company's SIC codes, borough, RV, and age — never generic filler.

**Streaming for perceived speed.**
All LLM responses stream via SSE. First words appear in under 2 seconds. Flask `stream_with_context` prevents proxy buffering. `X-Accel-Buffering: no` header disables nginx buffering on the DGX.

---

## Built at NVIDIA Hackathon

STELLA demonstrates what on-device AI unlocks for economic access. The DGX is not just compute — it is a privacy guarantee. No business data leaves the local network. The LLM, the data, and every calculation run on-premise.

The goal: prove that £950 million in backdated government money is findable and claimable today, by any London small business owner, with a tool that costs nothing to run.

**Live at:** `http://100.82.65.29:5001` (Tailscale) · `http://localhost:5001` (local)
