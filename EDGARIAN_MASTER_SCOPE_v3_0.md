# EDGARIAN
## Master Project Scope — v3.0
*Value Investor Research Platform · Built from scratch · April 2026*

> Companion doc: `edgarian-theme.md` — Design tokens, component library
> Rule: This document is the single source of truth. No v2.x carry-over.

---

# 1. Core Philosophy

Edgarian is a **company research tool for self-directed value investors.**

Built for the workflow: find a company → understand the business → read the filings → track smart money → watch for events.

**Principles:**
- One company page. Everything in one place.
- Every number cites its exact source — accession number + section + page
- No scores, no verdicts, no recommendations — investor draws conclusions
- Color (Green / Red / Amber) classifies filing type only — not investment advice
- 100% free data stack — edgartools + yfinance + SEC EDGAR

**Not:**
- A stock screener
- A recommendation engine
- A real-time trading terminal

---

# 2. Technology Stack

## 2.1 Data Layer

| Tool | Purpose | Cost |
|---|---|---|
| edgartools | All SEC EDGAR parsing — Form 4, 13F, 10-K, 8-K, XBRL, SC 13D | Free |
| yfinance | Daily price, market cap | Free |
| httpx | EDGAR RSS polling (real-time feed) | Free |
| spaCy / difflib | Risk factor text diff (Phase 1–2) | Free |
| sentence-transformers | Semantic risk factor diff (Phase 3+) | Free |
| pandas | XBRL data processing, financial modeling | Free |

## 2.2 Application Stack

- **Backend:** Python · FastAPI
- **Database:** PostgreSQL
- **Frontend:** React + CSS variables (edgarian-theme.md tokens)
- **Scheduler:** APScheduler — daily price refresh + score recompute
- **RSS Listener:** httpx async — real-time EDGAR feed
- **Auth:** Google OAuth (Authlib) — Phase 3
- **PDF Viewer:** PDF.js — in-app, slide-in drawer
- **Hosting:** Railway or Render (free tier)
- **Local DB:** Docker Compose (PostgreSQL + pgAdmin)

## 2.3 Price Data Strategy

| Use Case | Frequency | Source | Fallback |
|---|---|---|---|
| Price display on company page | Daily cron | yfinance | Last cached PostgreSQL value + staleness warning |
| Market cap display | Daily cron | yfinance | Last cached value |
| Merger arb spread | On-demand | yfinance | N/A |

**Rules:**
- All price displays show `"Price as of [timestamp]"`
- If yfinance fails, show last PostgreSQL cached value with `"Price data unavailable — last updated [date]"`
- Signal and analysis logic is never blocked by price data failure

---

# 3. App Structure

## 3.1 Pages

| Route | Description |
|---|---|
| `/` | Landing — ticker search only |
| `/company/:symbol` | Company research page — 5 tabs |
| `/feed` | Global real-time EDGAR filing feed |

No screener. No separate signals page. No special situations standalone page.
Everything lives inside `/company/:symbol`.

## 3.2 Landing Page (`/`)

- Full-page centered ticker search bar
- Eyebrow: `"Research any public company"`
- Subtext: `"Powered by SEC EDGAR public filings"`
- Recent searches (localStorage)
- No feed, no scores, no noise

## 3.3 Company Page (`/company/:symbol`)

### Header (always visible)
```
Company name (Georgia 32px bold)
Ticker · Sector · Exchange
Price  $XXX.XX  "Price as of [datetime]"
```

### 5 Tabs

#### Tab 1 — Earnings Quality (default)
- FCF vs Net Income — multi-year bar/line chart, divergence flagged
- Debt maturity schedule — bar chart by year
- D/E Model — 3 auto-computed scenarios (Base / Bull / Bear)
  - Base: debt rolled at current rates, FCF steady
  - Bull: FCF +10-15%, aggressive paydown
  - Bear: FCF compression, refinancing at higher rates
  - Output: D/E ratio projected annually, covenant breach flag if applicable
- Every data point: source citation → accession number + section + page → [open in viewer]

#### Tab 2 — Business
- Sankey chart: Revenue → Segments → Gross Profit → Operating Income → Net Income
  - Rendered via **`sankey-income-statement` skill** — see Section 13 for full spec
  - `sankey.py` produces the canonical JSON payload; skill renders the HTML output
- Segment table: current year vs prior year, YoY delta
- Data from XBRL (10-K / 10-Q)
- Every figure: source citation → accession number + section → [open in viewer]

#### Tab 3 — Filings & Risk
- **10-K Structured Reader:**
  - Risks (Item 1A)
  - Financial highlights (Item 8)
  - Management outlook & guidance (Item 7 MD&A)
  - Each section extracted and displayed with source citation
- **Risk Factor Delta:**
  - Side-by-side: this year vs last year
  - New risks (green highlight), expanded risks (amber), removed risks (red strikethrough)
  - Phase 1–2: difflib heuristic
  - Phase 3+: sentence-transformers semantic diff
- **Research Notes:**
  - Per-ticker textarea, auto-saved on blur
  - Timestamped: `"Last edited [date]"`
  - Auth-gated (Phase 3)

#### Tab 4 — Smart Money
- **Super Investor 13F Tracker (fixed 15):**

| # | Investor | Fund |
|---|---|---|
| 1 | Warren Buffett | Berkshire Hathaway |
| 2 | Bill Ackman | Pershing Square |
| 3 | Michael Burry | Scion Asset Management |
| 4 | David Einhorn | Greenlight Capital |
| 5 | Seth Klarman | Baupost Group |
| 6 | Howard Marks | Oaktree Capital |
| 7 | Mohnish Pabrai | Pabrai Funds |
| 8 | Guy Spier | Aquamarine Fund |
| 9 | Joel Greenblatt | Gotham Asset Management |
| 10 | Chris Hohn | TCI Fund Management |
| 11 | Francisco Garcia Parames | Cobas Asset Management |
| 12 | Li Lu | Himalaya Capital |
| 13 | David Tepper | Appaloosa Management |
| 14 | Bruce Berkowitz | Fairholme Fund |
| 15 | Prem Watsa | Fairfax Financial |

  - Per investor: current position size, QoQ change (added / reduced / exited / new)
  - Data lag label: `"13F data lag: up to 45 days"`
  - Source citation per row → accession number → [open in viewer]

- **Insider Activity:**
  - Open-market buys and sells only
  - 10b5-1 planned trades excluded
  - Cluster detection: multiple insiders, short window flagged
  - Per transaction: insider name, title, shares, price, date, accession number → [open in viewer]

#### Tab 5 — Events
- **Special Situations Timeline** (chronological, newest first):

| Event Type | Filing | Color |
|---|---|---|
| Spin-off announced | Form 10-12B | Green |
| Post-bankruptcy emergence | Form 15-12B | Green |
| Share buyback program | 8-K Item 8.01 | Green |
| Activist entry (>5% stake) | SC 13D | Green |
| Bankruptcy filing | 8-K Item 1.03 | Red |
| Reverse stock split | 8-K Item 5.03 | Red |
| Earnings restatement | 8-K Item 4.02 | Red |
| Equity offering / dilution | S-3 / 424B3 | Red |
| CEO / CFO change | 8-K Item 5.02 | Amber |
| M&A — target announced | DEFM14A + 8-K 1.01 | Amber |
| M&A — acquirer announced | 8-K Item 1.01 | Amber |
| Going private | SC 13E-3 | Amber |
| Tender offer | SC TO-T / SC TO-I | Amber |
| Rights offering | S-1 / 424B | Green |

- Each event row: color badge, event type, one-line plain-English summary, filing date, accession number → [open in viewer]
- M&A events show: counterparty name, deal size if available, merger arb spread if computable

## 3.4 Global Feed (`/feed`)

Real-time EDGAR RSS stream — all public companies, all filing types.

**Each feed row:**
```
[Color badge]  TICKER  Form Type  Plain-English summary  [time ago]  [accession#]
```

- **Company name** → links to `/company/:symbol`
- **Accession number** → links directly to SEC EDGAR filing
- Color classification applied per filing type (same table as Events tab)

**Filters (top of page):**
- Ticker / company name search
- Color: Green / Red / Amber
- Form type: 8-K / 13D / 13F / Form 4 / 10-K / Special Situations
- Feed mode: High Signal (top 10% by importance) / All Filings

**Source:** `https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=&dateb=&owner=include&count=40&output=atom`
Supplemental: efts.sec.gov full-text search API
Deduplication: by accession number

---

# 4. Source Citation System

Every extracted data point carries a source reference:

```
FCF: $4.2B
← 10-K · Item 8 · Cash Flow Statement
   Accession #0000320193-26-000123  [open in viewer]

New risk: "tariff exposure in Southeast Asia"
← 10-K · Item 1A · Risk Factors · ¶ 14
   Accession #0000320193-26-000123  [open in viewer]
```

**[open in viewer]** triggers the PDF drawer — slides in from right, opens to the exact page, pre-highlights the relevant passage.

### Citation fields stored per data point:
| Field | Description |
|---|---|
| `accession_no` | SEC filing accession number |
| `cik` | Company CIK (for URL generation) |
| `form_type` | 10-K / 8-K / Form 4 / 13F etc. |
| `source_section` | Item 1A / Item 8 / Note 6 etc. |
| `source_page` | Page number in PDF (for PDF.js `initialPage`) |
| `filing_date` | Date of the filing |

### Accession URL generation (deterministic, no API call):
```
Filing index:
https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&type=&dateb=&owner=include&count=40

Direct filing:
https://www.sec.gov/Archives/edgar/data/{cik}/{accession_no_no_dashes}/{accession_no}.txt
```

---

# 5. PDF Viewer — Slide-In Drawer

- **Trigger:** any `[open in viewer]` citation link
- **Animation:** slides in from right — `transform: translateX(100%)` → `translateX(0)`, `transition: 300ms ease`
- **Width:** 480px desktop; full-screen mobile
- **PDF.js:** renders filing PDF, jumps to `source_page`, pre-highlights `source_section` passage
- **Dismiss:** click outside drawer OR press Esc → slides back out
- **Notes:** per-filing textarea inside drawer, saved to `highlights` table (auth-gated)
- **Highlights:** color-coded freeform annotations, stored by `(user_id, accession_no, page, coords)`
- **Underlying page:** remains fully interactive while drawer is open

---

# 6. Database Schema (PostgreSQL)

### tickers
| Field | Type | Notes |
|---|---|---|
| symbol | text | PK |
| name | text | |
| cik | text | Never strip leading zeros |
| sector | text | |
| exchange | text | |
| price | numeric | |
| price_updated_at | timestamptz | Always timezone-aware |
| last_ingested_at | timestamptz | |

### financials
| Field | Type | Notes |
|---|---|---|
| id | serial | PK |
| ticker | text | FK → tickers |
| period | text | FY2024 / Q3 2024 |
| revenue | numeric | |
| gross_profit | numeric | |
| operating_income | numeric | |
| net_income | numeric | |
| free_cash_flow | numeric | |
| capex | numeric | |
| long_term_debt | numeric | |
| total_equity | numeric | |
| accession_no | text | Source filing |
| source_section | text | e.g. "Item 8" |
| source_page | int | For PDF.js |
| filing_date | date | |
| computed_at | timestamptz | |

### segments
| Field | Type | Notes |
|---|---|---|
| id | serial | PK |
| ticker | text | FK → tickers |
| period | text | |
| segment_name | text | |
| revenue | numeric | |
| operating_income | numeric | Nullable |
| accession_no | text | |
| source_section | text | |
| source_page | int | |
| filing_date | date | |

### debt_schedule
| Field | Type | Notes |
|---|---|---|
| id | serial | PK |
| ticker | text | FK → tickers |
| maturity_year | int | |
| amount | numeric | |
| instrument | text | Notes, bonds, credit facility |
| accession_no | text | |
| source_section | text | e.g. "Note 6" |
| source_page | int | |
| filing_date | date | |

### risk_factors
| Field | Type | Notes |
|---|---|---|
| id | serial | PK |
| ticker | text | FK → tickers |
| accession_no | text | |
| filing_year | int | |
| factor_text | text | Full extracted text |
| factor_hash | text | For deduplication |
| source_page | int | |
| filing_date | date | |

### risk_deltas
| Field | Type | Notes |
|---|---|---|
| id | serial | PK |
| ticker | text | FK → tickers |
| filing_year | int | Current year |
| delta_type | text | new / expanded / removed |
| factor_text | text | |
| prior_text | text | Nullable — for expanded |
| accession_no | text | Current filing |
| prior_accession_no | text | |
| source_page | int | |
| computed_at | timestamptz | |

### insider_trades
| Field | Type | Notes |
|---|---|---|
| id | serial | PK |
| ticker | text | FK → tickers |
| insider_name | text | |
| title | text | |
| transaction_type | text | buy / sell |
| shares | numeric | |
| price_per_share | numeric | |
| total_value | numeric | |
| is_10b5_1 | boolean | Always filter out if true |
| transaction_date | date | |
| accession_no | text | |
| source_page | int | |
| filing_date | date | |

### superinvestor_holdings
| Field | Type | Notes |
|---|---|---|
| id | serial | PK |
| investor_name | text | From fixed list of 15 |
| fund_name | text | |
| fund_cik | text | |
| ticker | text | FK → tickers |
| period | text | Q4 2025 etc. |
| shares_held | numeric | |
| market_value | numeric | |
| qoq_change | text | new / added / reduced / exited |
| qoq_change_pct | numeric | |
| accession_no | text | |
| source_page | int | |
| filing_date | date | |

### special_situations
| Field | Type | Notes |
|---|---|---|
| id | serial | PK |
| ticker | text | FK → tickers — nullable for unknown |
| situation_type | text | spin-off / bankruptcy / M&A etc. |
| filing_type | text | |
| color | text | green / red / amber |
| summary | text | Plain-English one-liner |
| accession_no | text | |
| cik | text | |
| source_page | int | |
| detected_at | timestamptz | |
| filing_date | date | |

### feed_events
| Field | Type | Notes |
|---|---|---|
| accession_no | text | PK |
| form_type | text | |
| company_name | text | |
| ticker | text | Nullable |
| cik | text | |
| signal_color | text | green / red / amber |
| summary | text | |
| filing_date | date | |
| detected_at | timestamptz | |
| priority_score | numeric | |

### users
| Field | Type | Notes |
|---|---|---|
| id | serial | PK |
| email | text | |
| google_id | text | |
| created_at | timestamptz | |

### notes
| Field | Type | Notes |
|---|---|---|
| id | serial | PK |
| user_id | int | FK → users |
| ticker | text | Scoped to ticker |
| note_text | text | |
| updated_at | timestamptz | |

### highlights
| Field | Type | Notes |
|---|---|---|
| id | serial | PK |
| user_id | int | FK → users |
| accession_no | text | |
| page | int | |
| coords | jsonb | |
| color | text | |
| note_text | text | |
| created_at | timestamptz | |

---

# 7. Frontend Page Map

| Route | Components |
|---|---|
| `/` | SearchBar, RecentSearches |
| `/company/:symbol` | CompanyHeader, TabBar, EarningsQuality, Business, FilingsRisk, SmartMoney, Events |
| `/feed` | FeedRow, FilterBar, ColorPill |
| `PdfDrawer` | Global overlay component, triggered by any citation link |

### Tab Components

| Tab | Key Components |
|---|---|
| EarningsQuality | FCFvsNIChart, DebtMaturityChart, DEModel |
| Business | SankeyChart, SegmentTable |
| FilingsRisk | TenKReader, RiskDeltaPanel, NotesPanel |
| SmartMoney | SuperInvestorTable, InsiderTable |
| Events | EventTimeline, EventRow |

---

# 8. Build Phases

| Phase | Name | Deliverables |
|---|---|---|
| 1 | Data Foundation | DB schema, edgartools integration, ticker ingest, 10-K XBRL parser, Form 4 parser, 13F parser |
| 2 | Company Page — Earnings & Business | FCF vs NI, debt schedule, D/E model, Sankey chart, segment table, source citations |
| 3 | Filings & Risk + Auth | 10-K reader, risk factor delta (difflib), Google OAuth, notes, PDF.js drawer, highlights |
| 4 | Smart Money | Super investor 13F tracker (fixed 15), insider activity, cluster detection |
| 5 | Events + Feed | Special situations timeline, global EDGAR RSS feed, feed filters |
| 6 | Intelligence Upgrade | sentence-transformers semantic risk diff, Phase 3+ NLP |

---

# 9. Global Coding Rules

All files, all phases. Non-negotiable.

```
1.  datetime.now(timezone.utc)               — never datetime.utcnow()
2.  from datetime import datetime, timezone  — always import timezone explicitly
3.  All timestamptz columns compared with timezone-aware datetimes only
4.  Upsert pattern: DELETE → INSERT          — never db.merge()
5.  All detectors/parsers: sync def          — no async def, no AsyncSession
6.  SQLAlchemy 2.0: select() + db.execute()  — never Query API
7.  Pydantic v2: model_config = ConfigDict(from_attributes=True)
8.  All env vars via pydantic-settings Settings class — never os.getenv() scattered
9.  No bare except — always except Exception as e with logging
10. All prices shown with timestamp: "Price as of [datetime]"
11. Signal deduplication: by (accession_no, ticker, signal_type) before insert
12. pandas / numpy: never pin exact version — use >= in requirements.txt
13. APScheduler: always use @asynccontextmanager lifespan in main.py
14. CORS: allowed_origins as comma-separated string in .env, split at runtime
15. SessionMiddleware added before CORSMiddleware in main.py
```

### edgartools Adapter Rules

```
16. Company(cik)                    — positional only, never Company(cik=cik)
17. set_identity(email)             — call before every Company() instantiation
18. user_agent= kwarg               — does not exist, never use it
19. xbrl.facts.get_concept(name)    — correct API, never xbrl.get()
20. xbrl.get_dimension_values()     — does not exist, use try/except per concept
21. reporting_owner on Form 4       — may be a list, always isinstance() check
22. non_derivative_table            — may be None, always getattr with None default
23. get_filings(form="10-K")        — single string only, not a list
24. CIK                             — never strip leading zeros, breaks EDGAR URLs
25. edgartools is sync              — never wrap in asyncio.run(), causes hang
```

### Frontend Rules

```
26. id="app" on root div            — required for dark/light toggle
27. localStorage theme init         — before React mounts in main.jsx, no flash
28. tokens.css                      — import in main.jsx, not auto-loaded
29. All colors via CSS vars         — never hardcode hex, breaks theme toggle
30. react-router                    — NavBar inside BrowserRouter context always
31. Vite dev port 5173              — must match CORS allowed_origins exactly
32. ScoreBlock / chart props        — pass pre-computed values, components don't derive internally
```

---

# 10. Super Investor CIKs (Fixed List)

CIKs required for 13F parsing via edgartools. Verify before Phase 4 build.

| Investor | Fund | CIK (verify) |
|---|---|---|
| Warren Buffett | Berkshire Hathaway | 0001067983 |
| Bill Ackman | Pershing Square | 0001336528 |
| Michael Burry | Scion Asset Management | 0001649339 |
| David Einhorn | Greenlight Capital | 0001079114 |
| Seth Klarman | Baupost Group | 0001061768 |
| Howard Marks | Oaktree Capital | 0001403528 |
| Mohnish Pabrai | Pabrai Funds | 0001173334 |
| Guy Spier | Aquamarine Fund | 0001159159 |
| Joel Greenblatt | Gotham Asset Management | 0001512093 |
| Chris Hohn | TCI Fund Management | 0001343816 |
| Francisco Garcia Parames | Cobas Asset Management | verify |
| Li Lu | Himalaya Capital | 0001709323 |
| David Tepper | Appaloosa Management | 0001006438 |
| Bruce Berkowitz | Fairholme Fund | 0001056831 |
| Prem Watsa | Fairfax Financial | 0001042046 |

---

# 11. Environment Variables

| Variable | Dev Value | Notes |
|---|---|---|
| `DATABASE_URL` | `postgresql://edgarian:edgarian@localhost:5432/edgarian` | |
| `SEC_USER_AGENT` | `your@email.com` | Required by SEC — set before uvicorn starts |
| `DEV_MODE` | `true` | Disables auth in Phase 1–2 |
| `SECRET_KEY` | `dev-insecure-key` | Session signing |
| `ALLOWED_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | Comma-separated |
| `GOOGLE_CLIENT_ID` | — | Phase 3 |
| `GOOGLE_CLIENT_SECRET` | — | Phase 3 |

---

# 12. Local Setup (Windows)

```powershell
# 1. Clone
git clone https://github.com/akshaynarkar/edgarian.git
cd edgarian
copy .env.example .env

# 2. Database
docker compose up -d

# 3. Backend
cd backend
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
$env:SEC_USER_AGENT="your@email.com"
uvicorn app.main:app --reload

# 4. Frontend
cd ..\frontend
npm install
npm run dev
```

---

# 13. Sankey Income Statement — Skill Integration

## 13.1 Skill Reference

Skill: `sankey-income-statement`
Renders interactive Plotly Sankey diagrams from pre-processed JSON. Does NOT parse XBRL.
Pipeline owner: `backend/app/analysis/sankey.py` → produces JSON → skill renders HTML.

## 13.2 Canonical JSON Contract

```json
{
  "ticker":   "NVDA",
  "logo_url": "https://logo.clearbit.com/nvidia.com",
  "title":    "NVIDIA FY2025 Income Statement",
  "period":   "FY2025",
  "currency": "USD",
  "unit":     "B",
  "nodes": [
    {"id": 0, "label": "Data Center",     "value": 115.2, "type": "revenue_segment"},
    {"id": 1, "label": "Gaming & Other",  "value": 15.3,  "type": "revenue_segment"},
    {"id": 2, "label": "Revenue",         "value": 130.5, "type": "revenue"},
    {"id": 3, "label": "Gross Profit",    "value": 97.9,  "type": "profit"},
    {"id": 4, "label": "Cost of Revenue", "value": 32.6,  "type": "cost"},
    {"id": 5, "label": "Operating Income","value": 81.5,  "type": "profit"},
    {"id": 6, "label": "R&D",             "value": 10.6,  "type": "cost"},
    {"id": 7, "label": "SG&A",            "value": 5.8,   "type": "cost"},
    {"id": 8, "label": "Net Income",      "value": 72.9,  "type": "profit"},
    {"id": 9, "label": "Income Tax",      "value": 11.1,  "type": "cost"},
    {"id": 10,"label": "Other (net)",     "value": 2.5,   "type": "other"}
  ],
  "links": [
    {"source": 0,  "target": 2,  "value": 115.2},
    {"source": 1,  "target": 2,  "value": 15.3},
    {"source": 2,  "target": 3,  "value": 97.9},
    {"source": 2,  "target": 4,  "value": 32.6},
    {"source": 3,  "target": 5,  "value": 81.5},
    {"source": 3,  "target": 6,  "value": 10.6},
    {"source": 3,  "target": 7,  "value": 5.8},
    {"source": 5,  "target": 8,  "value": 72.9},
    {"source": 5,  "target": 9,  "value": 11.1},
    {"source": 5,  "target": 10, "value": 2.5}
  ]
}
```

**Contract rules (guaranteed by `sankey.py` before passing to skill):**
- All `node.value` are positive — always `abs()` before serializing
- Link values are always positive
- `type` is one of: `revenue_segment` | `revenue` | `profit` | `cost` | `other`
- Revenue sub-segments may be absent — single `revenue` node with no incoming links is valid
- `logo_url` may be `null` — skill renders without logo gracefully
- Multiple periods passed as array for carousel navigation (one payload per period)

## 13.3 Logo Resolution — Option B (sankey.py)

Static dict for common tickers, yfinance fallback for long tail, `None` if both fail.

```python
LOGO_DOMAINS = {
    "AAPL":  "apple.com",
    "MSFT":  "microsoft.com",
    "GOOGL": "alphabet.com",
    "GOOG":  "alphabet.com",
    "AMZN":  "amazon.com",
    "META":  "meta.com",
    "NVDA":  "nvidia.com",
    "TSLA":  "tesla.com",
    "BRK.B": "berkshirehathaway.com",
    "JPM":   "jpmorganchase.com",
    "V":     "visa.com",
    "JNJ":   "jnj.com",
    "WMT":   "walmart.com",
    "UNH":   "unitedhealthgroup.com",
    "XOM":   "exxonmobil.com",
    "MA":    "mastercard.com",
    "PG":    "pg.com",
    "HD":    "homedepot.com",
    "CVX":   "chevron.com",
    "ABBV":  "abbvie.com",
}

def resolve_logo_url(ticker: str) -> str | None:
    if ticker in LOGO_DOMAINS:
        return f"https://logo.clearbit.com/{LOGO_DOMAINS[ticker]}"
    try:
        import yfinance as yf
        website = yf.Ticker(ticker).info.get("website", "")
        domain = website.replace("https://", "").replace("http://", "").split("/")[0]
        return f"https://logo.clearbit.com/{domain}" if domain else None
    except Exception:
        return None
```

## 13.4 XBRL → Sankey Node Mapping

| Node label | XBRL concept | Notes |
|---|---|---|
| Revenue segments | `RevenueFromContractWithCustomerExcludingAssessedTax` by dimension | Fallback: single Revenue node |
| Revenue | `Revenues` or `RevenueFromContractWithCustomerExcludingAssessedTax` | |
| Gross Profit | `GrossProfit` | |
| Cost of Revenue | `CostOfRevenue` | |
| Operating Income | `OperatingIncomeLoss` | |
| R&D | `ResearchAndDevelopmentExpense` | |
| SG&A | `SellingGeneralAndAdministrativeExpense` | |
| Net Income | `NetIncomeLoss` | |
| Income Tax | `IncomeTaxExpenseBenefit` | |
| Other (net) | Computed: `OperatingIncome - NetIncome - IncomeTax` | |

---

*EDGARIAN MASTER SCOPE · v3.0 · April 2026*
*Clean slate. Built for two friends who do serious value investing.*
*Companion: `edgarian-theme.md`*
