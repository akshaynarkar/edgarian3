from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any

from sqlalchemy import Select, desc, select
from sqlalchemy.orm import Session

from app.db.models import Financial

logger = logging.getLogger(__name__)


def _to_float(value: Decimal | float | int | None) -> float | None:
    if value is None:
        return None
    return float(value)


def _year_label(period: str | None, filing_date: Any) -> str:
    if period:
        return str(period)
    if filing_date is not None:
        try:
            return str(filing_date.year)
        except Exception as e:
            logger.warning("Unable to derive year label from filing_date: %s", e)
    return "Unknown"


def _divergence_flag(net_income: float | None, free_cash_flow: float | None) -> bool:
    if net_income is None or free_cash_flow is None:
        return False

    denominator = max(abs(net_income), 1.0)
    delta_ratio = abs(free_cash_flow - net_income) / denominator
    return delta_ratio >= 0.20


def _build_financials_stmt(symbol: str, limit: int) -> Select[tuple[Financial]]:
    return (
        select(Financial)
        .where(Financial.ticker == symbol.upper())
        .order_by(desc(Financial.filing_date), desc(Financial.id))
        .limit(limit)
    )


def build_earnings_quality(symbol: str, db: Session, years: int = 5) -> dict[str, Any]:
    records = list(db.execute(_build_financials_stmt(symbol, years)).scalars().all())
    records.reverse()

    chart_rows: list[dict[str, Any]] = []
    citations: list[dict[str, Any]] = []

    for record in records:
        net_income = _to_float(record.net_income)
        free_cash_flow = _to_float(record.free_cash_flow)
        divergence = _divergence_flag(net_income, free_cash_flow)

        row = {
            "year": _year_label(record.period, record.filing_date),
            "period": record.period,
            "net_income": net_income,
            "free_cash_flow": free_cash_flow,
            "divergence": divergence,
            "divergence_direction": (
                "fcf_below_ni"
                if net_income is not None and free_cash_flow is not None and free_cash_flow < net_income
                else "fcf_above_ni"
            ),
            "citation": {
                "accession_no": record.accession_no,
                "source_section": record.source_section or "Item 8",
                "source_page": record.source_page or 1,
                "filing_date": record.filing_date.isoformat() if record.filing_date else None,
            },
        }
        chart_rows.append(row)
        citations.append(row["citation"])

    latest = chart_rows[-1] if chart_rows else None
    divergence_years = [row["year"] for row in chart_rows if row["divergence"]]

    return {
        "symbol": symbol.upper(),
        "series": chart_rows,
        "summary": {
            "latest_period": latest["period"] if latest else None,
            "latest_net_income": latest["net_income"] if latest else None,
            "latest_free_cash_flow": latest["free_cash_flow"] if latest else None,
            "divergence_years": divergence_years,
            "has_recent_divergence": bool(latest and latest["divergence"]),
        },
        "citations": citations,
    }
