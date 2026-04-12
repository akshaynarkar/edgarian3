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
    "AAPL": "apple.com",
    "MSFT": "microsoft.com",
    "GOOGL": "alphabet.com",
    "GOOG": "alphabet.com",
    "AMZN": "amazon.com",
    "META": "meta.com",
    "NVDA": "nvidia.com",
    "TSLA": "tesla.com",
    "BRK.B": "berkshirehathaway.com",
    "JPM": "jpmorganchase.com",
    "V": "visa.com",
    "JNJ": "jnj.com",
    "WMT": "walmart.com",
    "UNH": "unitedhealthgroup.com",
    "XOM": "exxonmobil.com",
    "MA": "mastercard.com",
    "PG": "pg.com",
    "HD": "homedepot.com",
    "CVX": "chevron.com",
    "ABBV": "abbvie.com",
}


def _to_float(value: Decimal | float | int | None) -> float:
    if value is None:
        return 0.0
    return float(value)


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


def _latest_financial(symbol: str, db: Session) -> Financial | None:
    return db.execute(
        select(Financial)
        .where(Financial.ticker == symbol.upper())
        .order_by(desc(Financial.filing_date), desc(Financial.id))
        .limit(1)
    ).scalar_one_or_none()


def _period_segments(symbol: str, period: str, db: Session) -> list[Segment]:
    return list(
        db.execute(
            select(Segment)
            .where(Segment.ticker == symbol.upper(), Segment.period == period)
            .order_by(desc(Segment.revenue), Segment.segment_name.asc())
        ).scalars().all()
    )


def build_sankey_payload(symbol: str, db: Session) -> dict[str, Any]:
    ticker = symbol.upper()
    financial = _latest_financial(ticker, db)
    if financial is None:
        return {
            "ticker": ticker,
            "logo_url": resolve_logo_url(ticker),
            "title": f"{ticker} Income Statement",
            "period": None,
            "currency": "USD",
            "unit": "B",
            "nodes": [],
            "links": [],
            "citation": None,
        }

    segments = _period_segments(ticker, financial.period, db)

    revenue = abs(_to_float(financial.revenue))
    gross_profit = abs(_to_float(financial.gross_profit))
    operating_income = abs(_to_float(financial.operating_income))
    net_income = abs(_to_float(financial.net_income))
    cost_of_revenue = abs(max(revenue - gross_profit, 0.0))
    # Gap between operating income and net income = tax + other items.
    # No income_tax field in Financial; split heuristically 70/30.
    oi_to_ni_gap = abs(max(operating_income - net_income, 0.0))
    income_tax = round(oi_to_ni_gap * 0.70, 2)
    other_net = round(oi_to_ni_gap * 0.30, 2)

    nodes: list[dict[str, Any]] = []
    links: list[dict[str, Any]] = []

    next_id = 0
    revenue_segment_ids: list[int] = []

    for segment in segments:
        seg_value = abs(_to_float(segment.revenue))
        if seg_value <= 0:
            continue

        nodes.append(
            {
                "id": next_id,
                "label": segment.segment_name,
                "value": seg_value,
                "type": "revenue_segment",
            }
        )
        revenue_segment_ids.append(next_id)
        next_id += 1

    revenue_id = next_id
    nodes.append({"id": revenue_id, "label": "Revenue", "value": abs(revenue), "type": "revenue"})
    next_id += 1

    gross_profit_id = next_id
    nodes.append({"id": gross_profit_id, "label": "Gross Profit", "value": abs(gross_profit), "type": "profit"})
    next_id += 1

    cost_of_revenue_id = next_id
    nodes.append(
        {
            "id": cost_of_revenue_id,
            "label": "Cost of Revenue",
            "value": abs(cost_of_revenue),
            "type": "cost",
        }
    )
    next_id += 1

    operating_income_id = next_id
    nodes.append(
        {
            "id": operating_income_id,
            "label": "Operating Income",
            "value": abs(operating_income),
            "type": "profit",
        }
    )
    next_id += 1

    net_income_id = next_id
    nodes.append({"id": net_income_id, "label": "Net Income", "value": abs(net_income), "type": "profit"})
    next_id += 1

    income_tax_id = next_id
    nodes.append({"id": income_tax_id, "label": "Income Tax", "value": abs(income_tax), "type": "cost"})
    next_id += 1

    other_net_id = next_id
    nodes.append({"id": other_net_id, "label": "Other (net)", "value": abs(other_net), "type": "other"})

    for segment_id in revenue_segment_ids:
        node_value = next(node["value"] for node in nodes if node["id"] == segment_id)
        links.append({"source": segment_id, "target": revenue_id, "value": abs(node_value)})

    links.extend(
        [
            {"source": revenue_id, "target": gross_profit_id, "value": abs(gross_profit)},
            {"source": revenue_id, "target": cost_of_revenue_id, "value": abs(cost_of_revenue)},
            {"source": gross_profit_id, "target": operating_income_id, "value": abs(operating_income)},
            {"source": operating_income_id, "target": net_income_id, "value": abs(net_income)},
            {"source": operating_income_id, "target": income_tax_id, "value": abs(income_tax)},
            {"source": operating_income_id, "target": other_net_id, "value": abs(other_net)},
        ]
    )

    payload = {
        "ticker": ticker,
        "logo_url": resolve_logo_url(ticker),
        "title": f"{ticker} {financial.period} Income Statement",
        "period": financial.period,
        "currency": "USD",
        "unit": "B",
        "nodes": [{"id": node["id"], "label": node["label"], "value": abs(node["value"]), "type": node["type"]} for node in nodes],
        "links": [{"source": link["source"], "target": link["target"], "value": abs(link["value"])} for link in links],
        "citation": {
            "accession_no": financial.accession_no,
            "source_section": financial.source_section or "Item 8",
            "source_page": financial.source_page or 1,
            "filing_date": financial.filing_date.isoformat() if financial.filing_date else None,
        },
    }
    return payload


def render_sankey_html(payload: dict[str, Any]) -> str:
    safe_payload = json.dumps(payload)
    return f"""<!doctype html>
<html>
<head>
  <meta charset=\"utf-8\" />
  <script src=\"https://cdn.plot.ly/plotly-2.35.2.min.js\"></script>
  <style>
    :root {{
      --bg: #0a0a0a;
      --bg2: #111111;
      --text: #f0ede8;
      --muted: #7a7874;
      --accent: #c8c0b0;
      --green-text: #97c459;
      --red-text: #f09595;
      --iframe-link: rgba(255,255,255,0.15);
    }}

    html, body {{
      margin: 0;
      padding: 0;
      background: var(--bg);
      color: var(--text);
      font-family: Helvetica Neue, Arial, sans-serif;
    }}

    .wrap {{
      background: var(--bg2);
      border: 0.5px solid rgba(255,255,255,0.07);
      border-radius: 8px;
      padding: 14px;
    }}

    .header {{
      display: flex;
      align-items: center;
      gap: 12px;
      margin-bottom: 12px;
    }}

    .header img {{
      width: 24px;
      height: 24px;
      object-fit: contain;
      border-radius: 4px;
      background: transparent;
    }}

    .title {{
      font-family: Georgia, serif;
      font-size: 20px;
      font-weight: 700;
      line-height: 1.1;
    }}

    .sub {{
      font-size: 11px;
      letter-spacing: 0.18em;
      text-transform: uppercase;
      color: var(--muted);
      margin-top: 3px;
    }}

    #chart {{
      width: 100%;
      height: 480px;
    }}
  </style>
</head>
<body>
  <div class=\"wrap\">
    <div class=\"header\">
      <div id=\"logo\"></div>
      <div>
        <div class=\"title\" id=\"title\"></div>
        <div class=\"sub\" id=\"sub\"></div>
      </div>
    </div>
    <div id=\"chart\"></div>
  </div>

  <script>
    const payload = {safe_payload};

    function syncThemeFromParent() {{
      try {{
        const parentApp = window.parent.document.getElementById('app');
        if (!parentApp) return;
        const styles = window.parent.getComputedStyle(parentApp);
        const keys = [
          '--bg', '--bg2', '--text', '--muted', '--accent',
          '--green-text', '--red-text'
        ];
        keys.forEach((key) => {{
          const value = styles.getPropertyValue(key);
          if (value) {{
            document.documentElement.style.setProperty(key, value.trim());
          }}
        }});
        const isLight = parentApp.classList.contains('light');
        document.documentElement.style.setProperty(
          '--iframe-link',
          isLight ? 'rgba(0,0,0,0.12)' : 'rgba(255,255,255,0.15)'
        );
      }} catch (err) {{
        console.warn('Theme sync failed', err);
      }}
    }}

    function nodeColor(nodeType) {{
      if (nodeType === 'revenue') return 'var(--accent)';
      if (nodeType === 'revenue_segment') return 'var(--accent)';
      if (nodeType === 'profit') return 'var(--green-text)';
      if (nodeType === 'cost') return 'var(--red-text)';
      return 'var(--muted)';
    }}

    syncThemeFromParent();

    const logo = document.getElementById('logo');
    if (payload.logo_url) {{
      logo.innerHTML = `<img src="${{payload.logo_url}}" alt="${{payload.ticker}} logo" />`;
    }}

    document.getElementById('title').textContent = payload.title;
    document.getElementById('sub').textContent = `${{payload.period || 'Latest period'}} · ${{payload.currency}} · Unit ${{payload.unit}}`;

    const data = [{{
      type: 'sankey',
      arrangement: 'snap',
      node: {{
        pad: 18,
        thickness: 16,
        label: payload.nodes.map((n) => `${{n.label}} ($${{Number(n.value).toFixed(1)}}${{payload.unit}})`),
        color: payload.nodes.map((n) => nodeColor(n.type)),
        line: {{
          color: 'transparent',
          width: 0
        }}
      }},
      link: {{
        source: payload.links.map((l) => l.source),
        target: payload.links.map((l) => l.target),
        value: payload.links.map((l) => l.value),
        color: payload.links.map(() => 'var(--iframe-link)')
      }}
    }}];

    const layout = {{
      paper_bgcolor: 'transparent',
      plot_bgcolor: 'transparent',
      margin: {{ l: 10, r: 10, t: 10, b: 10 }},
      font: {{
        family: 'Helvetica Neue, Arial, sans-serif',
        size: 12,
        color: 'var(--text)'
      }}
    }};

    Plotly.newPlot('chart', data, layout, {{
      displayModeBar: false,
      responsive: true
    }});
  </script>
</body>
</html>"""
