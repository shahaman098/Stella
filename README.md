# STELLA

**On-device AI agent that finds unclaimed government money for London small businesses.**

STELLA cross-references three government datasets, computes exact pound figures using statutory rules, and produces a ready-to-send claim letter — all in under 10 seconds, entirely offline on an NVIDIA DGX.

---

## The Problem

£317 million in Small Business Rate Relief goes unclaimed every year across London. 141,248 eligible properties (117,188 at full relief, 24,060 in the taper band) are paying rates they legally do not owe. Backdated to April 2023 — the start of the current rating list — that is **£950 million** sitting in borough council accounts that belongs to small business owners.

The government does not notify eligible businesses. Councils do not apply the relief automatically. Most owners have no idea it exists.

STELLA fixes that.

---

## What It Does

**Street Scanner** — Enter any London postcode. STELLA returns every eligible commercial property, the exact annual saving, the backdated lump sum, confidence level, and the specific statutory rule that makes it applicable. One postcode lookup surfaces the entire unclaimed opportunity on that street.

**My Business** — Enter a business name and postcode. STELLA verifies the company on Companies House, matches it to the VOA property record, computes SBRR eligibility, finds matching grants, generates an eligibility tracker with 8 insight cards, and produces a ready-to-send claim letter — all specific to that business.

**Priority Scanner** — Select a London borough. STELLA scans all eligible properties, cross-matches Companies House to find the actual business at each address, ranks by unclaimed value, and shows the top 50 opportunities for outreach.

**AI Application Drafter** — For each matched grant, STELLA streams a complete application package: eligibility narrative, professional email (under 120 words, ready to send), documents checklist, and step-by-step application guide — drafted by Nemotron running locally on DGX.

---

## Financial Impact

| Metric | Figure |
|--------|--------|
| London commercial properties (VOA 2026) | 311,750 |
| Properties eligible for 100% SBRR | 117,188 |
| Properties eligible for tapered SBRR | 24,060 |
| Total unclaimed SBRR per year | £316,910,648 |
| Backdated value (3 years from April 2023) | £950,731,945 |
| Boroughs with direct council contacts | 33 |
| Grant programmes matched | 12 |
| Companies House records indexed | 5,607,936 |

Top 5 London boroughs by eligible properties: Tower Hamlets (10,636), Westminster (9,216), City of London (7,581), Camden (6,555), Southwark (5,608).

A single café at RV £8,500 in Camden is owed: £3,247/yr in SBRR + £9,741 backdated to April 2023. STELLA finds this in 8 seconds and drafts the claim letter.

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                    Flask UI (port 5001)              │
│              server/templates/index.html             │
│    Street Scanner · My Business · Priority Scanner  │
└────────────────┬────────────────────────────────────┘
                 │ REST + SSE streaming
┌────────────────▼────────────────────────────────────┐
│                  server/app.py                       │
│   /api/lookup · /api/biz-profile · /api/insights    │
│   /api/priority-scan · /api/grant-application       │
│   /api/draft-email · /api/draft-grant               │
└──────┬──────────┬──────────┬──────────┬─────────────┘
       │          │          │          │
  ┌────▼───┐ ┌───▼────┐ ┌───▼────┐ ┌──▼──────────┐
  │  VOA   │ │   CH   │ │ Relief │ │  LLM Layer  │
  │  CSV   │ │  DB    │ │ Engine │ │  agent/llm  │
  │311,750 │ │5.6M    │ │rules_  │ │  Nemotron   │
  │records │ │records │ │relief  │ │  (DGX Spark)│
  └────────┘ └────────┘ └───┬────┘ └─────────────┘
                             │
                        ┌────▼────┐
                        │ Grants  │
                        │ Engine  │
                        │rules_   │
                        │grants   │
                        └─────────┘
```

### Data Layer

**VOA 2026 Revaluation** (`data/voa_london_index.csv`, 41MB, committed to repo)
- 311,750 London commercial properties
- Fields: UARN, borough, address, postcode, sector, rateable value, SCAT code, composite flag
- Sourced from Valuation Office Agency open data
- Preprocessed into sector-classified CSV for fast lookups

**Companies House Bulk Register** (`data/ch_index.db`, 1.2GB SQLite, local only)
- 5,607,936 companies, all with postcodes and SIC codes
- Built from `BasicCompanyDataAsOneFile-2026-06-01.zip` via `data/ingest_companies_local.py`
- FTS5 virtual table for sub-50ms full-text company name search
- Postcode index for instant cross-matching with VOA properties

**Borough Contacts** (`data/borough_contacts.py`)
- 33 London boroughs + City of London
- Direct business rates team email, phone, and SBRR application URL per borough
- Always includes gov.uk fallback URL (council-specific pages sometimes 403)

### Computation Layer

**Relief Engine** (`engines/rules_relief.py`) — deterministic, LLM-free

Implements England 2026/27 business rates rules exactly:

- 2026/27 multipliers from gov.uk notification 2/2026:
  - Small business RHL (retail/cafe/pub/hospitality/leisure): 0.382p per £1 RV
  - Small business non-RHL: 0.432p per £1 RV
  - Standard RHL: 0.430p per £1 RV (RV £51k–£499k)
  - High value: 0.508p per £1 RV (RV ≥ £500k)
- SBRR: 100% if RV ≤ £12,000; tapered 1% per £30 for £12,000–£15,000
- Pub/live-music relief: 15% additional, pubs only (per gov.uk publication 1/2026)
- SSB 2026 transitional relief where applicable
- Backdated value: 3-year conservative estimate from April 2023

Every pound figure is traceable to a specific statutory source. The LLM never touches these numbers.

**Grants Engine** (`engines/rules_grants.py`) — sector-specific matching

12 grant programmes with genuine eligibility gates (not shown to everyone):

| Grant | Gate |
|-------|------|
| Start Up Loan | Company age ≤ 5 years only |
| UKSPF | Deprived/outer borough OR high-street sector |
| London Growth Hub | All London SMEs (universal entry point) |
| Innovate UK Smart Grants | Tech/R&D/manufacturing SIC codes only |
| R&D Tax Credits | Tech/manufacturing/health SIC codes only |
| GLA Good Growth Fund | Creative sector OR east/deprived boroughs |
| Hospitality Energy Grant | Café/pub/food SIC codes only |
| ELBP Grant | East London boroughs only |
| Creative Enterprise | Creative/cultural SIC codes only |
| Made Smarter | Manufacturing SIC codes only |
| High Streets Heritage | Retail in deprived/outer areas |
| Net Zero Support | All businesses (with sector-specific reasoning) |

All `match_reasons` are generated from actual company data: name, RV, SIC codes, borough, age.

### Intelligence Layer

**LLM Client** (`agent/llm.py`)

Streaming OpenAI-compatible client with automatic fallback:

1. Primary: DGX Spark at `http://10.18.216.24:30000` (Nemotron, `max_tokens: 4096`)
2. Fallback: Ollama at `http://localhost:11434` (llama3.2)

Nemotron is a reasoning model — it uses tokens for chain-of-thought before writing content. `max_tokens: 4096` is required; lower values produce empty responses.

All LLM calls use Server-Sent Events (SSE) streaming so text appears word-by-word. Flask `stream_with_context` + `Response(mimetype="text/event-stream")`. Wire format: `data: {"t": "chunk"}\n\n`, terminated by `data: [DONE]\n\n`.

**Eligibility Tracker** (`/api/insights`) — 8 insight card types

Rendered at the top of every My Business result, sorted by priority:

1. **SBRR status** — ELIGIBLE / TAPERED / NOT ELIGIBLE with exact £/yr and backdated figure
2. **Total money on table** — SBRR + number of grants cross-referenced
3. **Backdating urgency** — specific £ figure, cites April 2023, warns councils can refuse beyond 6 years
4. **RV cliff warning** — fires if within £1,500 of full-relief or tapered thresholds
5. **Location bonus** — east/deprived boroughs unlock ELBP, higher UKSPF allocation, GLA Good Growth
6. **Sector peer comparison** — your RV vs median of all same-sector businesses in same borough
7. **Named peers at postcode** — other businesses at the same postcode, their RVs and eligibility
8. **London-wide context** — 117,188 properties, £317M/yr, why you must apply (not automatic)

---

## API Reference

All endpoints accept and return JSON (except streaming endpoints which are SSE).

### `POST /api/biz-profile`
Full My Business analysis: CH verification + VOA match + SBRR + grants.
```json
{ "name": "Prufrock Coffee", "postcode": "EC1N 7TE" }
```
Returns: `property`, `ch_profile`, `ch_verification`, `sic_codes`, `company_age_years`, `grants`, `council`, `biz_name`.

### `POST /api/insights`
Eligibility tracker cards for a business.
```json
{
  "rateable_value": 8500, "sector": "cafe", "borough": "Camden",
  "postcode": "WC2H 7NA", "biz_name": "Prufrock Coffee",
  "grants": [...], "sbrr_saving": 3247
}
```
Returns: `{ "insights": [ { "type", "icon", "title", "body", "color", "action_url" } ] }`.

### `POST /api/lookup`
Street Scanner: postcode → all properties with SBRR analysis.
```json
{ "query": "WC2H 7NA" }
```
Returns: `businesses[]` each with `findings[]`, `totals`.

### `POST /api/priority-scan`
Borough scan: top unclaimed-money businesses.
```json
{ "borough": "Camden", "limit": 20 }
```
Returns: `properties[]` each with `companies[]` cross-matched from CH.

### `POST /api/grant-application` (SSE streaming)
Full 4-section grant application package.
```json
{ "grant": { ...grantObject }, "business": { ...bizObject } }
```
Streams: Section 1 (why you qualify), Section 2 (email), Section 3 (documents), Section 4 (steps).

### `POST /api/draft-email` / `POST /api/draft-grant` (SSE streaming)
Quick email or action steps for a single grant. `mode: "email"` or `mode: "steps"`.

---

## Running Locally

### Requirements

- Python 3.10+
- Flask (`pip install flask`)
- DGX Spark on local network at `http://10.18.216.24:30000` (or Ollama as fallback)
- `data/ch_index.db` — build instructions below
- `data/voa_london_index.csv` — included in repo

### Start the server

```bash
git clone https://github.com/shahaman098/Stella
cd Stella
pip install flask

# With Companies House API (recommended for full verification):
export COMPANIES_HOUSE_KEY=your_key_here  # free at developer.company-information.service.gov.uk

# Start server (port 5001 by default):
python3 server/app.py

# Or specify port and expose on network:
PORT=5000 python3 server/app.py
```

Open `http://localhost:5001` (or `http://100.82.65.29:5001` via Tailscale).

### Build the CH index (one-time, ~30 minutes)

The Companies House bulk data is 1.2GB and not committed to git.

```bash
# Download from Companies House (free, no login):
curl -O "https://download.companieshouse.gov.uk/BasicCompanyDataAsOneFile-2026-06-01.zip"
unzip BasicCompanyDataAsOneFile*.zip -d data/ch_raw/

# Ingest into SQLite (takes ~25 mins, builds 1.2GB index):
python3 data/ingest_companies_local.py

# Verify:
python3 -c "
import sqlite3
c = sqlite3.connect('data/ch_index.db').cursor()
c.execute('SELECT COUNT(*) FROM companies')
print(f'{c.fetchone()[0]:,} companies indexed')
"
# Should print: 5,607,936 companies indexed
```

### Offline deployment on DGX

After cloning and building the CH index, zero internet is required:

```bash
# No COMPANIES_HOUSE_KEY set = full offline mode
# VOA: in repo
# CH: local SQLite
# LLM: DGX Spark on local network
# All calculations: pure Python

python3 server/app.py
```

Copy the CH index from another machine:
```bash
scp data/ch_index.db user@100.109.237.73:/path/to/Stella/data/
```

### Environment variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `PORT` | `5001` | Flask server port |
| `COMPANIES_HOUSE_KEY` | _(empty)_ | CH API key — offline mode if unset |
| `DGX_URL` | `http://10.18.216.24:30000` | LLM endpoint |
| `DGX_MODEL` | `nemotron` | Model name |
| `OLLAMA_URL` | `http://localhost:11434` | Ollama fallback |
| `OLLAMA_MODEL` | `llama3.2` | Ollama model |

---

## Data Sources

| Dataset | Source | Size | Update frequency |
|---------|--------|------|-----------------|
| VOA 2026 Rating List | Valuation Office Agency open data | 41MB CSV | Revaluation (every 3 years) |
| Companies House Bulk | companieshouse.gov.uk/about/dataProducts | 1.2GB ZIP | Monthly |
| SBRR rules | gov.uk/apply-for-business-rate-relief | Statutory | Per Autumn Statement |
| 2026/27 multipliers | gov.uk notification 2/2026 | Statutory | Annual |
| Borough contacts | Individual council websites | Static | Manually maintained |
| Grant programmes | Various (GLA, UKRI, BBB, HMRC) | Static | Manually maintained |

All financial calculations are traceable to a specific gov.uk source. The LLM layer never modifies or generates pound figures.

---

## Project Structure

```
Stella/
├── server/
│   ├── app.py                    # Flask server, all API routes (896 lines)
│   └── templates/
│       └── index.html            # Single-page UI (1,244 lines)
├── engines/
│   ├── rules_relief.py           # SBRR + rates calculation engine
│   └── rules_grants.py           # Grant eligibility matching engine
├── agent/
│   ├── llm.py                    # DGX/Ollama streaming LLM client
│   └── pipeline.py               # Postcode-to-findings pipeline
├── data/
│   ├── voa_london_index.csv      # 311,750 VOA properties (in repo, 41MB)
│   ├── ch_index.db               # 5.6M companies SQLite (local only, 1.2GB)
│   ├── borough_contacts.py       # 33 borough contact details
│   ├── ingest_companies_local.py # CH bulk → SQLite ingest + search
│   ├── ingest_companies.py       # CH live API client
│   └── ingest_voa.py             # VOA raw data → indexed CSV
├── tests/
│   └── test_rules_relief.py      # Deterministic rule tests
├── run.py                        # CLI interface
└── DATASETS.md                   # Full data provenance
```

---

## Key Design Decisions

**LLM never touches the numbers.** The relief engine and grants engine are pure Python running statutory rules. The LLM only writes prose — emails, summaries, application text. This means every pound figure is auditable and explainable without an AI.

**Offline first.** Every core function works without internet. VOA data is in the repo. CH data is a local SQLite. The LLM runs on DGX on the local network. The CH live API is an optional enhancement for higher-confidence company verification, not a dependency.

**Tailored, not generic.** Grants only show when there is a specific reason for that business. R&D Tax Credits never appear for a café. ELBP never appears for a Westminster office. Every match reason references actual company data from that specific lookup.

**Streaming for speed perception.** All LLM calls stream via SSE. The first words appear in under 2 seconds even when the full response takes 30. Flask `stream_with_context` prevents buffering at the proxy layer.

---

## Roadmap

- [ ] IoD 2019 deprivation index integration (unlocks more targeted grant matching)
- [ ] Automated form submission via browser automation (Claude Computer Use)
- [ ] TfL disruption data feed (hospitality businesses near construction eligible for compensation)
- [ ] gov.uk Find a Grant full pagination (currently 101 grants, paginator broken)
- [ ] Multi-property disqualification checker (SBRR requires single-property occupation)
- [ ] Email delivery to council directly from UI

---

## Built at NVIDIA Hackathon

STELLA was built to demonstrate what on-device AI can do for economic access. The DGX is not just the compute — it is the privacy guarantee. No business data leaves the local network. The LLM, the data, and the computation all run on-premise.

The goal is not a product. It is proof that £950 million in backdated government money is findable and claimable today, by any London small business owner, with a tool that costs nothing to run.
