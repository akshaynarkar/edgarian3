from __future__ import annotations

from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analysis.debt_model import build_debt_model
from app.analysis.earnings_quality import build_earnings_quality
from app.analysis.sankey import build_sankey_payload, render_sankey_html
from app.db.database import get_db
from app.db.models import Segment, Ticker

router = APIRouter(prefix="/company", tags=["company"])


def _serialize_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, list):
        return [_serialize_value(item) for item in value]
    if isinstance(value, dict):
        return {key: _serialize_value(item) for key, item in value.items()}
    return value


def _build_segment_table(symbol: str, db: Session) -> list[dict[str, Any]]:
    rows = list(
        db.execute(
            select(Segment)
            .where(Segment.ticker == symbol.upper())
            .order_by(Segment.filing_date.desc(), Segment.period.desc(), Segment.segment_name.asc())
        ).scalars().all()
    )
    if not rows:
        return []

    ordered_periods: list[str] = []
    for row in rows:
        if row.period not in ordered_periods:
            ordered_periods.append(row.period)

    current_period = ordered_periods[0]
    prior_period = ordered_periods[1] if len(ordered_periods) > 1 else None
    current_rows = [row for row in rows if row.period == current_period]
    prior_lookup = {
        row.segment_name: row
        for row in rows
        if prior_period is not None and row.period == prior_period
    }

    table: list[dict[str, Any]] = []
    for row in current_rows:
        prior_row = prior_lookup.get(row.segment_name)
        current_revenue = float(row.revenue) if row.revenue is not None else None
        prior_revenue = float(prior_row.revenue) if prior_row and prior_row.revenue is not None else None
        yoy_delta = None
        if current_revenue is not None and prior_revenue not in (None, 0):
            yoy_delta = ((current_revenue - prior_revenue) / prior_revenue) * 100
        table.append({
            "segment_name": row.segment_name,
            "current_period": current_period,
            "prior_period": prior_period,
            "current_revenue": current_revenue,
            "prior_revenue": prior_revenue,
            "current_operating_income": float(row.operating_income) if row.operating_income is not None else None,
            "prior_operating_income": float(prior_row.operating_income) if prior_row and prior_row.operating_income is not None else None,
            "yoy_delta_pct": round(yoy_delta, 2) if yoy_delta is not None else None,
            "citation": {
                "accession_no": row.accession_no,
                "source_section": row.source_section or "Item 8",
                "source_page": row.source_page or 1,
                "filing_date": row.filing_date.isoformat() if row.filing_date else None,
            },
        })
    return table


@router.get("/{symbol}")
def get_company(
    symbol: str,
    db: Session = Depends(get_db),
    years: int = Query(default=6, ge=1, le=20, description="Number of years for earnings/debt history"),
) -> dict[str, Any]:
    normalized_symbol = symbol.upper()
    ticker = db.execute(
        select(Ticker).where(Ticker.symbol == normalized_symbol)
    ).scalar_one_or_none()

    if ticker is None:
        raise HTTPException(status_code=404, detail=f"Ticker not found: {normalized_symbol}")

    earnings = build_earnings_quality(normalized_symbol, db, years=years)
    debt = build_debt_model(normalized_symbol, db, years=years)
    sankey_payload = build_sankey_payload(normalized_symbol, db)
    sankey_html = render_sankey_html(sankey_payload)
    segments = _build_segment_table(normalized_symbol, db)

    response = {
        "company": {
            "symbol": ticker.symbol,
            "name": ticker.name,
            "sector": ticker.sector,
            "exchange": ticker.exchange,
            "price": float(ticker.price) if ticker.price is not None else None,
            "price_updated_at": ticker.price_updated_at.isoformat() if ticker.price_updated_at else None,
            "price_label": (
                f"Price as of {ticker.price_updated_at.isoformat()}"
                if ticker.price_updated_at else None
            ),
        },
        "tabs": {
            "earnings_quality": earnings,
            "business": {
                "sankey_payload": sankey_payload,
                "sankey_html": sankey_html,
                "segments": segments,
            },
            "debt": debt,
        },
    }
    return _serialize_value(response)
