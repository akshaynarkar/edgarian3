from __future__ import annotations

import json
import logging
from decimal import Decimal
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.db.models import Financial, Segment

logger = logging.getLogger(__name__)

LOGO_DOMAINS = {
    "AAPL": "apple.com", "MSFT": "microsoft.com", "GOOGL": "alphabet.com",
    "GOOG": "alphabet.com", "AMZN": "amazon.com", "META": "meta.com",
    "NVDA": "nvidia.com", "TSLA": "tesla.com", "BRK.B": "berkshirehathaway.com",
    "JPM": "jpmorganchase.com", "V": "visa.com", "JNJ": "jnj.com",
    "WMT": "walmart.com", "UNH": "unitedhealthgroup.com", "XOM": "exxonmobil.com",
    "MA": "mastercard.com", "PG": "pg.com", "HD": "homedepot.com",
    "CVX": "chevron.com", "ABBV": "abbvie.com",
}

_GEO_KEYWORDS = {
    "americas", "europe", "china", "japan", "asia", "pacific", "rest of world",
    "international", "domestic", "united states", "u.s.", "emea", "apac",
    "latin america", "middle east", "africa", "canada", "australia",
    "greater china", "other countries",
}


def _to_float(value: Decimal | float | int | None) -> float:
    if value is None:
        return 0.0
    return float(value)


def _yoy(current: float, prior: float) -> float | None:
    if prior == 0:
        return None
    return round(((current - prior) / abs(prior)) * 100, 1)


def resolve_logo_url(ticker: str) -> str | None:
    ticker = ticker.upper()
    if ticker in LOGO_DOMAINS:
        return f"https://logo.clearbit.com/{LOGO_DOMAINS[ticker]}"
    try:
        import yfinance as yf
        website = yf.Ticker(ticker).info.get("website", "")
        domain = website.replace("https://", "").replace("http://", "").split("/")[0]
        return f"https://logo.clearbit.com/{domain}" if domain else None
    except Exception as e:
        logger.warning("Unable to resolve logo for %s: %s", ticker, e)
        return None


def _latest_two_financials(symbol: str, db: Session) -> tuple[Financial | None, Financial | None]:
    rows = list(db.execute(
        select(Financial)
        .where(Financial.ticker == symbol.upper())
        .order_by(desc(Financial.filing_date), desc(Financial.id))
        .limit(2)
    ).scalars().all())
    current = rows[0] if len(rows) > 0 else None
    prior = rows[1] if len(rows) > 1 else None
    return current, prior


def _period_segments(symbol: str, period: str, db: Session) -> list[Segment]:
    return list(db.execute(
        select(Segment)
        .where(Segment.ticker == symbol.upper(), Segment.period == period)
        .order_by(desc(Segment.revenue), Segment.segment_name.asc())
    ).scalars().all())


def _is_geo_segment(name: str) -> bool:
    return any(kw in name.lower() for kw in _GEO_KEYWORDS)


def _select_best_segment_set(segments: list[Segment], revenue: float) -> list[Segment]:
    if not segments:
        return []
    geo = [s for s in segments if _is_geo_segment(s.segment_name)]
    product = [s for s in segments if not _is_geo_segment(s.segment_name)]
    if not geo:
        return product
    if not product:
        return geo

    def score(segs: list[Segment]) -> float:
        total = sum(_to_float(s.revenue) for s in segs)
        if revenue <= 0:
            return abs(total)
        ratio = total / revenue
        if ratio > 1.2:
            return float("inf")
        return abs(ratio - 1.0)

    if score(geo) < score(product) - 0.05:
        return geo
    return product


def build_sankey_payload(symbol: str, db: Session) -> dict[str, Any]:
    ticker = symbol.upper()
    financial, prior_financial = _latest_two_financials(ticker, db)

    if financial is None:
        return {
            "ticker": ticker, "logo_url": resolve_logo_url(ticker),
            "title": f"{ticker} Income Statement", "period": None, "prior_period": None,
            "currency": "USD", "unit": "B", "nodes": [], "links": [], "citation": None,
        }

    all_segments = _period_segments(ticker, financial.period, db)

    revenue = abs(_to_float(financial.revenue))
    gross_profit = abs(_to_float(financial.gross_profit))
    operating_income = abs(_to_float(financial.operating_income))
    net_income = abs(_to_float(financial.net_income))
    cost_of_revenue = max(revenue - gross_profit, 0.0)
    opex = max(gross_profit - operating_income, 0.0)
    oi_gap = max(operating_income - net_income, 0.0)
    income_tax = round(oi_gap * 0.70, 2)
    other_net = round(oi_gap * 0.30, 2)

    p_rev = abs(_to_float(prior_financial.revenue)) if prior_financial else 0.0
    p_gp = abs(_to_float(prior_financial.gross_profit)) if prior_financial else 0.0
    p_oi = abs(_to_float(prior_financial.operating_income)) if prior_financial else 0.0
    p_ni = abs(_to_float(prior_financial.net_income)) if prior_financial else 0.0
    p_cor = max(p_rev - p_gp, 0.0) if prior_financial else 0.0
    p_opex = max(p_gp - p_oi, 0.0) if prior_financial else 0.0

    segments = _select_best_segment_set(all_segments, revenue)
    seg_sum = sum(abs(_to_float(s.revenue)) for s in segments if _to_float(s.revenue) > 0)
    scale = (revenue / seg_sum) if seg_sum > 0 and revenue > 0 and abs(seg_sum - revenue) / revenue > 0.05 else 1.0

    prior_segs: dict[str, float] = {}
    if prior_financial:
        for s in _period_segments(ticker, prior_financial.period, db):
            prior_segs[s.segment_name] = abs(_to_float(s.revenue))

    nodes: list[dict[str, Any]] = []
    links: list[dict[str, Any]] = []
    nid = 0
    seg_ids: list[int] = []

    for seg in segments:
        v = abs(_to_float(seg.revenue)) * scale
        if v <= 0:
            continue
        pv = prior_segs.get(seg.segment_name, 0.0) * scale
        nodes.append({"id": nid, "label": seg.segment_name, "value": v, "type": "revenue_segment", "yoy": _yoy(v, pv) if pv else None})
        seg_ids.append(nid)
        nid += 1

    revenue_id = nid; nodes.append({"id": nid, "label": "Revenue", "value": revenue, "type": "revenue", "yoy": _yoy(revenue, p_rev)}); nid += 1
    gp_id = nid;      nodes.append({"id": nid, "label": "Gross Profit", "value": gross_profit, "type": "profit", "yoy": _yoy(gross_profit, p_gp)}); nid += 1
    cor_id = nid;     nodes.append({"id": nid, "label": "Cost of Revenue", "value": cost_of_revenue, "type": "cost", "yoy": _yoy(cost_of_revenue, p_cor)}); nid += 1
    oi_id = nid;      nodes.append({"id": nid, "label": "Operating Income", "value": operating_income, "type": "profit", "yoy": _yoy(operating_income, p_oi)}); nid += 1
    opex_id = nid;    nodes.append({"id": nid, "label": "Operating Expenses", "value": opex, "type": "cost", "yoy": _yoy(opex, p_opex)}); nid += 1
    ni_id = nid;      nodes.append({"id": nid, "label": "Net Income", "value": net_income, "type": "profit", "yoy": _yoy(net_income, p_ni)}); nid += 1
    tax_id = nid;     nodes.append({"id": nid, "label": "Income Tax", "value": income_tax, "type": "cost", "yoy": None}); nid += 1
    other_id = nid;   nodes.append({"id": nid, "label": "Other (net)", "value": other_net, "type": "other", "yoy": None})

    for sid in seg_ids:
        v = next(n["value"] for n in nodes if n["id"] == sid)
        links.append({"source": sid, "target": revenue_id, "value": v})

    links += [
        {"source": revenue_id, "target": gp_id,    "value": gross_profit},
        {"source": revenue_id, "target": cor_id,   "value": cost_of_revenue},
        {"source": gp_id,      "target": oi_id,    "value": operating_income},
        {"source": gp_id,      "target": opex_id,  "value": opex},
        {"source": oi_id,      "target": ni_id,    "value": net_income},
        {"source": oi_id,      "target": tax_id,   "value": income_tax},
        {"source": oi_id,      "target": other_id, "value": other_net},
    ]
    links = [l for l in links if l["value"] > 0]

    return {
        "ticker": ticker,
        "logo_url": resolve_logo_url(ticker),
        "title": f"{ticker} {financial.period} Income Statement",
        "period": financial.period,
        "prior_period": prior_financial.period if prior_financial else None,
        "currency": "USD", "unit": "B",
        "nodes": [{"id": n["id"], "label": n["label"], "value": abs(n["value"]), "type": n["type"], "yoy": n.get("yoy")} for n in nodes],
        "links": [{"source": l["source"], "target": l["target"], "value": abs(l["value"])} for l in links],
        "citation": {
            "accession_no": financial.accession_no,
            "source_section": financial.source_section or "Item 8",
            "source_page": financial.source_page or 1,
            "filing_date": financial.filing_date.isoformat() if financial.filing_date else None,
        },
    }


def render_sankey_html(payload: dict[str, Any]) -> str:
    safe_payload = json.dumps(payload)
    return f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8"/>
  <script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
  <style>
    html, body {{ margin:0; padding:0; height:100%; font-family:'Helvetica Neue',Arial,sans-serif; background:#111111; color:#f0ede8; }}
    body.light {{ background:#f4f2ee; color:#18170f; }}
    .wrap {{ background:#111111; border-radius:8px; padding:14px; height:100%; box-sizing:border-box; display:flex; flex-direction:column; }}
    body.light .wrap {{ background:#f4f2ee; }}
    .header {{ display:flex; align-items:center; gap:12px; margin-bottom:10px; flex-shrink:0; }}
    .header img {{ width:24px; height:24px; object-fit:contain; border-radius:4px; }}
    .title {{ font-family:Georgia,serif; font-size:18px; font-weight:700; line-height:1.1; }}
    .sub {{ font-size:10px; letter-spacing:0.18em; text-transform:uppercase; color:#7a7874; margin-top:3px; }}
    body.light .sub {{ color:#6b6760; }}
    #chart {{ flex:1; min-height:0; }}
  </style>
</head>
<body>
<div class="wrap">
  <div class="header">
    <div id="logo"></div>
    <div><div class="title" id="title"></div><div class="sub" id="sub"></div></div>
  </div>
  <div id="chart"></div>
</div>
<script>
const payload = {safe_payload};

function syncTheme() {{
  try {{
    const p = window.parent.document.getElementById('app');
    document.body.classList.toggle('light', p ? p.classList.contains('light') : false);
  }} catch(e) {{
    document.body.classList.toggle('light', window.matchMedia('(prefers-color-scheme:light)').matches);
  }}
}}
syncTheme();

window.addEventListener('message', e => {{
  if (e.data?.type === 'edgarian-theme') {{ document.body.classList.toggle('light', e.data.isLight); redraw(); }}
}});

const NODE_COLORS = {{ revenue_segment:'#5B9BD5', revenue:'#2E75B6', profit:'#70AD47', cost:'#FF6B6B', other:'#A0A0A0' }};
const LINK_COLORS = {{ revenue:'rgba(46,117,182,0.28)', profit:'rgba(112,173,71,0.28)', cost:'rgba(255,107,107,0.28)', other:'rgba(160,160,160,0.22)', revenue_segment:'rgba(91,155,213,0.28)' }};

function fmtVal(v) {{ return '$' + (v/1e9).toFixed(1) + (payload.unit||'B'); }}
function fmtYoy(y) {{ if(y==null) return ''; return (y>=0?'+':'') + y.toFixed(1) + '% Y/Y'; }}
function nodeLabel(n) {{
  let s = n.label + '<br>' + fmtVal(n.value);
  if (n.yoy != null) s += '<br>' + fmtYoy(n.yoy);
  return s;
}}

// Logo + header
const logo = document.getElementById('logo');
if (payload.logo_url) {{
  const img = document.createElement('img');
  img.src = payload.logo_url; img.alt = payload.ticker;
  img.onerror = () => img.style.display='none';
  logo.appendChild(img);
}}
document.getElementById('title').textContent = payload.title;
document.getElementById('sub').textContent =
  (payload.period||'Latest') + (payload.prior_period ? ' vs '+payload.prior_period : '') +
  ' \u00b7 ' + (payload.currency||'USD') + ' \u00b7 UNIT ' + (payload.unit||'B');

// Column assignment for profit-first vertical ordering
function col(n) {{
  if (n.type==='revenue_segment') return 0;
  if (n.type==='revenue') return 1;
  if (n.label==='Gross Profit'||n.label==='Cost of Revenue') return 2;
  if (n.label==='Operating Income'||n.label==='Operating Expenses') return 3;
  return 4;
}}
const COL_X = [0.02, 0.22, 0.48, 0.70, 0.95];

function computePositions() {{
  const groups = {{}};
  payload.nodes.forEach(n => {{
    const c = col(n);
    if (!groups[c]) groups[c] = [];
    groups[c].push(n);
  }});
  const nx = {{}}, ny = {{}};
  Object.entries(groups).forEach(([c, grp]) => {{
    const x = COL_X[+c] ?? 0.5;
    // profit/revenue types first, then cost/other
    grp.sort((a,b) => {{
      const rank = t => (t==='profit'||t==='revenue'||t==='revenue_segment') ? 0 : 1;
      return rank(a.type) - rank(b.type);
    }});
    const total = grp.reduce((s,n)=>s+n.value,0) || 1;
    let cum = 0.02;
    grp.forEach(n => {{
      nx[n.id] = x;
      const frac = n.value/total;
      ny[n.id] = Math.min(0.97, cum + frac/2);
      cum += frac;
    }});
  }});
  return {{nx, ny}};
}}

function buildTrace() {{
  const isLight = document.body.classList.contains('light');
  const bg = isLight ? '#f4f2ee' : '#111111';
  const fc = isLight ? '#18170f' : '#f0ede8';
  const typeMap = {{}};
  payload.nodes.forEach(n => typeMap[n.id] = n.type);
  const {{nx, ny}} = computePositions();
  return {{
    data: [{{
      type:'sankey', arrangement:'fixed',
      node: {{
        pad:12, thickness:13,
        label: payload.nodes.map(n => nodeLabel(n)),
        color: payload.nodes.map(n => NODE_COLORS[n.type]||'#A0A0A0'),
        x: payload.nodes.map(n => nx[n.id]??0.5),
        y: payload.nodes.map(n => ny[n.id]??0.5),
        line: {{color:'transparent', width:0}}
      }},
      link: {{
        source: payload.links.map(l=>l.source),
        target: payload.links.map(l=>l.target),
        value:  payload.links.map(l=>l.value),
        color:  payload.links.map(l=>LINK_COLORS[typeMap[l.target]]||'rgba(160,160,160,0.22)')
      }}
    }}],
    layout: {{
      paper_bgcolor:bg, plot_bgcolor:bg, autosize:true,
      margin:{{l:6,r:6,t:6,b:6}},
      font:{{family:"'Helvetica Neue',Arial,sans-serif", size:11, color:fc}}
    }}
  }};
}}

function redraw() {{
  const {{data,layout}} = buildTrace();
  Plotly.react('chart', data, layout, {{displayModeBar:false, responsive:true}});
}}

const {{data,layout}} = buildTrace();
Plotly.newPlot('chart', data, layout, {{displayModeBar:false, responsive:true}});
</script>
</body>
</html>"""
