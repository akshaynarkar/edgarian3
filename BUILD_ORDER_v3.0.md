# Edgarian — Build Order v3.0
*One phase per chat session. Each phase is self-contained and deployable.*
*ChatGPT writes code. Claude reviews, tests, debugs.*

---

## Session Workflow

```
1. Start new chat
2. Paste the phase prompt (bottom of each phase section)
3. ChatGPT generates code
4. Paste into Claude for review / debug
5. Fix, commit, push to GitHub
6. Start next phase
```

---

## Global Coding Rules (All Phases)

```
1.  datetime.now(timezone.utc)               — never datetime.utcnow()
2.  from datetime import datetime, timezone  — always import timezone explicitly
3.  All timestamptz columns compared with timezone-aware datetimes only
4.  Upsert pattern: DELETE → INSERT          — never db.merge()
5.  All parsers/detectors: sync def          — no async def, no AsyncSession
6.  SQLAlchemy 2.0: select() + db.execute()  — never Query API
7.  Pydantic v2: model_config = ConfigDict(from_attributes=True)
8.  All env vars via pydantic-settings Settings class — never os.getenv() scattered
9.  No bare except — always except Exception as e with logging
10. All prices shown with timestamp: "Price as of [datetime]"
11. Deduplication: by (accession_no, ticker) before every insert
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
27. localStorage theme init         — in main.jsx before React mounts, no flash
28. tokens.css                      — import explicitly in main.jsx
29. All colors via CSS vars         — never hardcode hex, breaks theme toggle
30. NavBar inside BrowserRouter     — always, useLocation() requires router context
31. Vite dev port 5173              — must match CORS allowed_origins exactly
32. Chart/table props               — pass pre-computed values, never derive internally
```

---

## Phase 1 — Data Foundation 🔲 NEXT
**Goal:** Working data pipeline. DB seeded. No UI.

| # | File | Description |
|---|---|---|
| 1.1 | `docker-compose.yml` | PostgreSQL + pgAdmin |
| 1.2 | `.env.example` | All env vars documented |
| 1.3 | `backend/app/config.py` | pydantic-settings Settings class |
| 1.4 | `backend/app/db/models.py` | All ORM models — v3.0 schema |
| 1.5 | `backend/app/db/database.py` | SQLAlchemy engine + SessionLocal |
| 1.6 | `migrations/` | Alembic init + first migration |
| 1.7 | `backend/requirements.txt` | All Python deps (pandas/numpy unpinned) |
| 1.8 | `backend/app/ingestion/ticker_ingest.py` | Ticker → CIK via edgartools |
| 1.9 | `backend/app/ingestion/tenk_parser.py` | 10-K XBRL: financials, segments, debt schedule |
| 1.10 | `backend/app/ingestion/form4_parser.py` | Form 4: insider trades (sync, no asyncio) |
| 1.11 | `backend/app/ingestion/thirteenf_parser.py` | 13F: super investor holdings (fixed 15 CIKs) |
| 1.12 | `backend/app/main.py` | FastAPI app, lifespan, CORS, /health |
| 1.13 | `backend/app/utils/date_utils.py` | within_days, in_window, to_date helpers |

**Done when:**
```
GET /health → {"status": "ok"}
ticker_ingest("AAPL") → tickers row written
tenk_parser("AAPL") → financials + segments + debt_schedule rows written
```

**ChatGPT session prompt:**
> Build Edgarian Phase 1 — Data Foundation. Refer to EDGARIAN_MASTER_SCOPE_v3.0.md and edgarian-theme.md.
> Deliver all 13 files. Follow all Global Coding Rules and edgartools Adapter Rules exactly.
> DB schema: v3.0 (financials, segments, debt_schedule, risk_factors, risk_deltas, insider_trades, superinvestor_holdings, special_situations, feed_events, users, notes, highlights, tickers).
> No UI. No routers except /health.

---

## Phase 2 — Company Page: Earnings & Business 🔲
**Goal:** Tab 1 (Earnings Quality) + Tab 2 (Business) fully functional with real data.

| # | File | Description |
|---|---|---|
| 2.1 | `backend/app/analysis/earnings_quality.py` | FCF vs NI multi-year, divergence flag |
| 2.2 | `backend/app/analysis/debt_model.py` | Debt maturity schedule + D/E 3-scenario model |
| 2.3 | `backend/app/analysis/sankey.py` | Sankey JSON: XBRL→canonical payload for `sankey-income-statement` skill (see Scope Section 13) |
| 2.4 | `backend/app/routers/company.py` | GET /company/:symbol — all tab data |
| 2.5 | `backend/app/main.py` | Add company router |
| 2.6 | `frontend/src/theme/tokens.css` | All CSS vars from edgarian-theme.md |
| 2.7 | `frontend/src/main.jsx` | Root, theme init from localStorage |
| 2.8 | `frontend/src/App.jsx` | BrowserRouter, routes |
| 2.9 | `frontend/src/components/NavBar.jsx` | Nav, dark/light toggle |
| 2.10 | `frontend/src/pages/Landing.jsx` | Search bar only, recent searches |
| 2.11 | `frontend/src/pages/Company.jsx` | Company page shell + TabBar |
| 2.12 | `frontend/src/components/tabs/EarningsQuality.jsx` | FCF vs NI chart, debt chart, D/E model |
| 2.13 | `frontend/src/components/tabs/Business.jsx` | Sankey chart, segment table |
| 2.14 | `frontend/src/components/CitationLink.jsx` | "[open in viewer]" trigger component |

**Citation rule:** Every financial figure rendered must include `<CitationLink>` with accession_no + source_section + source_page.

**Done when:**
```
/company/AAPL → Tab 1 shows FCF vs NI chart + debt schedule + D/E model
              → Tab 2 shows Sankey + segment table
              → Every figure has [open in viewer] citation
```

**Chart specs (mandatory):**
- **FCF vs NI chart:** Vertical bar/line combo. X axis = year. Y axis = dollar value ($). Use Recharts (`ComposedChart` — `Bar` for NI, `Line` for FCF). Divergence flagged with color. Never horizontal.
- **Debt maturity chart:** Vertical bar chart. X axis = maturity year. Y axis = debt amount ($). Use Recharts `BarChart`. Never horizontal.
- **Sankey chart:** `sankey.py` outputs canonical JSON per Scope Section 13 contract. Skill `sankey-income-statement` renders the HTML. `sankey.py` must: `abs()` all node values, resolve `logo_url` via Option B (static dict + yfinance fallback), pass `ticker` as top-level field. Frontend `Business.jsx` embeds the skill's HTML output in an iframe or div.

**ChatGPT session prompt:**
> Build Edgarian Phase 2 — Company Page Earnings & Business tabs. Refer to EDGARIAN_MASTER_SCOPE_v3.0.md and edgarian-theme.md.
> Backend: earnings_quality.py, debt_model.py, sankey.py, company router (GET /company/:symbol).
> Frontend: tokens.css, main.jsx, App.jsx, NavBar, Landing, Company shell, EarningsQuality tab, Business tab, CitationLink component.
> Charts: FCF vs NI = Recharts ComposedChart (vertical, year X axis, $ Y axis). Debt maturity = Recharts BarChart (vertical, year X axis, $ Y axis).
> Sankey: sankey.py outputs canonical JSON per Scope Section 13. Always abs() all node values before serializing. Resolve logo_url via Option B (LOGO_DOMAINS static dict + yfinance fallback, None if both fail). Pass ticker as top-level field. Business.jsx embeds the returned HTML in an iframe.
> D/E model: 3 auto-computed scenarios (Base/Bull/Bear), no user input yet.
> Every data point must carry accession_no + source_section + source_page for citation.
> Follow all Global Coding Rules and Frontend Rules.

---

## Phase 3 — Filings & Risk + Auth 🔲
**Goal:** Tab 3 functional. PDF drawer working. Auth gating notes/highlights.

| # | File | Description |
|---|---|---|
| 3.1 | `backend/app/ingestion/risk_factor_parser.py` | Extract Item 1A risk factors from 10-K |
| 3.2 | `backend/app/analysis/risk_delta.py` | YoY diff — new / expanded / removed (difflib) |
| 3.3 | `backend/app/analysis/tenk_reader.py` | Structured extraction: risks, financials, guidance |
| 3.4 | `backend/app/routers/auth.py` | Google OAuth (Authlib) |
| 3.5 | `backend/app/routers/notes.py` | GET / POST /notes?ticker=X |
| 3.6 | `backend/app/routers/highlights.py` | CRUD /highlights |
| 3.7 | `backend/app/main.py` | Add auth, notes, highlights routers + SessionMiddleware |
| 3.8 | `frontend/src/components/tabs/FilingsRisk.jsx` | 10-K reader, risk delta panel |
| 3.9 | `frontend/src/components/PdfDrawer.jsx` | Slide-in from right, PDF.js, dismiss on outside click / Esc |
| 3.10 | `frontend/src/components/NotesPanel.jsx` | Ticker-scoped textarea, auto-save |

**PDF Drawer spec:**
- `transform: translateX(100%)` → `translateX(0)`, `transition: 300ms ease`
- Width: 480px desktop, full-screen mobile
- Opens to `initialPage` from citation, pre-highlights `source_section`
- Dismiss: click outside OR Esc key
- Notes textarea inside drawer, saved to highlights table

**Done when:**
```
/company/AAPL → Tab 3 shows structured 10-K reader
              → Risk delta shows new/expanded/removed risks highlighted
              → [open in viewer] opens PDF drawer to correct page
              → Notes save per ticker (auth-gated)
```

**ChatGPT session prompt:**
> Build Edgarian Phase 3 — Filings & Risk tab + Auth + PDF Drawer. Refer to EDGARIAN_MASTER_SCOPE_v3.0.md and edgarian-theme.md.
> Backend: risk_factor_parser, risk_delta (difflib), tenk_reader, Google OAuth (Authlib), notes router, highlights router.
> Frontend: FilingsRisk tab, PdfDrawer (slide-in from right, 300ms ease, PDF.js, initialPage, dismiss on outside click/Esc), NotesPanel.
> SessionMiddleware must be added before CORSMiddleware in main.py.
> Follow all Global Coding Rules and Frontend Rules.

---

## Phase 4 — Smart Money 🔲
**Goal:** Tab 4 — super investor tracker + insider activity.

| # | File | Description |
|---|---|---|
| 4.1 | `backend/app/ingestion/thirteenf_parser.py` | 13F parser for fixed 15 CIKs |
| 4.2 | `backend/app/analysis/superinvestors.py` | QoQ change: new/added/reduced/exited |
| 4.3 | `backend/app/analysis/insider_activity.py` | Cluster detection, 10b5-1 filter |
| 4.4 | `backend/app/routers/company.py` | Add smart_money data to /company/:symbol |
| 4.5 | `frontend/src/components/tabs/SmartMoney.jsx` | SuperInvestorTable + InsiderTable |

**Super investor rules:**
- Fixed 15 CIKs only (see scope Section 10)
- Data lag label: `"13F data lag: up to 45 days"` always shown
- QoQ change: compare current period vs prior period holdings

**Insider rules:**
- Open-market transactions only
- 10b5-1 trades excluded (`is_10b5_1 = true` filtered out)
- Cluster flag: ≥3 insiders buying within 30-day window

**Done when:**
```
/company/AAPL → Tab 4 shows which of the 15 super investors hold AAPL
              → QoQ change shown per investor
              → Insider buys/sells listed, clusters flagged
              → Every row has accession link
```

**ChatGPT session prompt:**
> Build Edgarian Phase 4 — Smart Money tab. Refer to EDGARIAN_MASTER_SCOPE_v3.0.md and edgarian-theme.md.
> Backend: 13F parser for fixed 15 super investor CIKs, QoQ change detection, insider activity with cluster detection and 10b5-1 filtering.
> Frontend: SmartMoney tab — SuperInvestorTable (investor, shares, market value, QoQ change badge) + InsiderTable (name, title, buy/sell, shares, value, date, accession link).
> Data lag label "13F data lag: up to 45 days" always visible.
> Follow all Global Coding Rules, edgartools Adapter Rules, and Frontend Rules.

---

## Phase 5 — Events + Global Feed 🔲
**Goal:** Tab 5 + /feed page live.

| # | File | Description |
|---|---|---|
| 5.1 | `backend/app/ingestion/feed_listener.py` | Async EDGAR RSS poller (httpx) |
| 5.2 | `backend/app/analysis/special_situations.py` | All 14 SS types — detect + classify |
| 5.3 | `backend/app/analysis/prioritization.py` | Feed ordering by importance score |
| 5.4 | `backend/app/routers/feed.py` | GET /feed — paginated, filtered |
| 5.5 | `backend/app/scheduler/cron_jobs.py` | Daily price refresh + RSS poll |
| 5.6 | `backend/app/main.py` | Add feed router + scheduler lifespan |
| 5.7 | `frontend/src/components/tabs/Events.jsx` | Special situations timeline |
| 5.8 | `frontend/src/pages/Feed.jsx` | Global feed, filters, color pills |
| 5.9 | `frontend/src/components/FeedRow.jsx` | Single feed row — color badge, links |

**Feed row spec:**
- Company name → `/company/:symbol`
- Accession number → SEC EDGAR direct URL (deterministic, no API call)
- Color badge: Green / Red / Amber per filing type classification

**Special situations — all 14 types:**
Spin-off, Post-bankruptcy emergence, Share buyback, Activist entry,
Bankruptcy filing, Reverse split, Earnings restatement, Equity offering,
CEO/CFO change, M&A target, M&A acquirer, Going private, Tender offer, Rights offering.

**Done when:**
```
/feed → live EDGAR events with color, plain-English summary, dual links
/company/AAPL → Tab 5 shows special situations timeline
```

**ChatGPT session prompt:**
> Build Edgarian Phase 5 — Events tab + Global Feed. Refer to EDGARIAN_MASTER_SCOPE_v3.0.md and edgarian-theme.md.
> Backend: EDGAR RSS poller (httpx async), all 14 special situation detectors, prioritization engine, /feed router (paginated, filter by color/form_type/ticker/mode).
> Frontend: Events tab (timeline, event rows with color badge + accession link), Feed page (FeedRow component — company name links to /company/:symbol, accession number links to SEC EDGAR).
> Scheduler: APScheduler lifespan in main.py — daily price refresh + RSS poll every 5 min.
> Follow all Global Coding Rules and Frontend Rules.

---

## Phase 6 — Intelligence Upgrade 🔲
**Goal:** Semantic NLP for risk factor delta.

| # | File | Description |
|---|---|---|
| 6.1 | `backend/app/nlp/semantic_diff.py` | sentence-transformers risk factor semantic diff |
| 6.2 | `backend/app/analysis/risk_delta.py` | Swap difflib → semantic diff |

**NLP outputs:**
- `"New risk introduced"`
- `"Existing risk expanded"`
- `"Language intensified"`

**Done when:**
```
Risk factor delta in Tab 3 uses semantic similarity, not just string diff.
```

**ChatGPT session prompt:**
> Build Edgarian Phase 6 — Semantic NLP upgrade. Refer to EDGARIAN_MASTER_SCOPE_v3.0.md.
> Replace difflib in risk_delta.py with sentence-transformers semantic similarity.
> Outputs: "New risk introduced" / "Existing risk expanded" / "Language intensified".
> Non-blocking — Phase 3 difflib output format must be preserved as fallback.

---

## Frontend File Map (All Phases)

| File | Phase | Status |
|---|---|---|
| `tokens.css` | 2 | 🔲 |
| `main.jsx` | 2 | 🔲 |
| `App.jsx` | 2 | 🔲 |
| `NavBar.jsx` | 2 | 🔲 |
| `pages/Landing.jsx` | 2 | 🔲 |
| `pages/Company.jsx` | 2 | 🔲 |
| `components/tabs/EarningsQuality.jsx` | 2 | 🔲 |
| `components/tabs/Business.jsx` | 2 | 🔲 |
| `components/CitationLink.jsx` | 2 | 🔲 |
| `components/tabs/FilingsRisk.jsx` | 3 | 🔲 |
| `components/PdfDrawer.jsx` | 3 | 🔲 |
| `components/NotesPanel.jsx` | 3 | 🔲 |
| `components/tabs/SmartMoney.jsx` | 4 | 🔲 |
| `components/tabs/Events.jsx` | 5 | 🔲 |
| `pages/Feed.jsx` | 5 | 🔲 |
| `components/FeedRow.jsx` | 5 | 🔲 |

---

## Repo Structure (Target)

```
edgarian/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── db/
│   │   │   ├── database.py
│   │   │   └── models.py
│   │   ├── ingestion/
│   │   │   ├── ticker_ingest.py
│   │   │   ├── tenk_parser.py
│   │   │   ├── form4_parser.py
│   │   │   ├── thirteenf_parser.py
│   │   │   └── feed_listener.py
│   │   ├── analysis/
│   │   │   ├── earnings_quality.py
│   │   │   ├── debt_model.py
│   │   │   ├── sankey.py
│   │   │   ├── risk_factor_parser.py
│   │   │   ├── risk_delta.py
│   │   │   ├── tenk_reader.py
│   │   │   ├── superinvestors.py
│   │   │   ├── insider_activity.py
│   │   │   ├── special_situations.py
│   │   │   └── prioritization.py
│   │   ├── nlp/
│   │   │   └── semantic_diff.py
│   │   ├── routers/
│   │   │   ├── company.py
│   │   │   ├── feed.py
│   │   │   ├── auth.py
│   │   │   ├── notes.py
│   │   │   ├── highlights.py
│   │   │   └── portfolio.py
│   │   ├── scheduler/
│   │   │   └── cron_jobs.py
│   │   └── utils/
│   │       └── date_utils.py
│   ├── migrations/
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── main.jsx
│   │   ├── App.jsx
│   │   ├── theme/
│   │   │   └── tokens.css
│   │   ├── pages/
│   │   │   ├── Landing.jsx
│   │   │   ├── Company.jsx
│   │   │   └── Feed.jsx
│   │   └── components/
│   │       ├── NavBar.jsx
│   │       ├── CitationLink.jsx
│   │       ├── PdfDrawer.jsx
│   │       ├── NotesPanel.jsx
│   │       ├── FeedRow.jsx
│   │       └── tabs/
│   │           ├── EarningsQuality.jsx
│   │           ├── Business.jsx
│   │           ├── FilingsRisk.jsx
│   │           ├── SmartMoney.jsx
│   │           └── Events.jsx
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml
├── .env.example
├── EDGARIAN_MASTER_SCOPE_v3.0.md
├── edgarian-theme.md
├── BUILD_ORDER_v3.0.md
└── README.md
```

---

*EDGARIAN BUILD ORDER · v3.0 · April 2026*
*Clean slate. Six phases. One company page.*
