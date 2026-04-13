from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.db.models import DebtSchedule, Financial

logger = logging.getLogger(__name__)


def _to_float(value: Decimal | float | int | None) -> float | None:
    if value is None:
        return None
    return float(value)


def _safe_div(numerator: float, denominator: float) -> float | None:
    if denominator == 0:
        return None
    return numerator / denominator


def _aggregate_debt_rows(rows: list[DebtSchedule]) -> list[dict[str, Any]]:
    grouped: dict[int, dict[str, Any]] = defaultdict(
        lambda: {"maturity_year": 0, "amount": 0.0, "instruments": [], "citations": []}
    )
    for row in rows:
        bucket = grouped[row.maturity_year]
        bucket["maturity_year"] = row.maturity_year
        bucket["amount"] += _to_float(row.amount) or 0.0
        if row.instrument:
            bucket["instruments"].append(row.instrument)
        bucket["citations"].append({
            "accession_no": row.accession_no,
            "source_section": row.source_section or "Note 6",
            "source_page": row.source_page or 1,
            "filing_date": row.filing_date.isoformat() if row.filing_date else None,
        })
    return sorted(grouped.values(), key=lambda item: item["maturity_year"])


def _build_scenario_rows(latest_financial: Financial, debt_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    current_year = datetime.now(timezone.utc).year
    total_equity = _to_float(latest_financial.total_equity) or 0.0
    starting_debt = _to_float(latest_financial.long_term_debt) or sum(row["amount"] for row in debt_rows)
    steady_fcf = _to_float(latest_financial.free_cash_flow) or 0.0

    scenario_inputs = {
        "Base": {"fcf_growth": 0.00, "paydown_ratio": 0.05, "roll_rate": 0.050},
        "Bull": {"fcf_growth": 0.12, "paydown_ratio": 0.15, "roll_rate": 0.045},
        "Bear": {"fcf_growth": -0.18, "paydown_ratio": 0.02, "roll_rate": 0.075},
    }

    rows: list[dict[str, Any]] = []
    for scenario_name, config in scenario_inputs.items():
        debt_balance = starting_debt
        fcf = steady_fcf
        projections: list[dict[str, Any]] = []
        for offset in range(5):
            year = current_year + offset
            paydown = max(fcf * config["paydown_ratio"], 0.0)
            debt_balance = max(debt_balance - paydown, 0.0)
            projected_equity = max(total_equity + (fcf * 0.20), 1.0)
            de_ratio = _safe_div(debt_balance, projected_equity)
            projections.append({
                "year": str(year),
                "de_ratio": round(de_ratio, 4) if de_ratio is not None else None,
                "debt_balance": round(debt_balance, 2),
                "projected_equity": round(projected_equity, 2),
                "fcf": round(fcf, 2),
                "refinancing_rate": round(config["roll_rate"] * 100, 2),
                "covenant_breach": bool(de_ratio is not None and de_ratio > 2.50),
                "citation": {
                    "accession_no": latest_financial.accession_no,
                    "source_section": latest_financial.source_section or "Item 8",
                    "source_page": latest_financial.source_page or 1,
                    "filing_date": latest_financial.filing_date.isoformat() if latest_financial.filing_date else None,
                },
            })
            fcf = fcf * (1 + config["fcf_growth"])
        rows.append({
            "scenario": scenario_name,
            "assumptions": {
                "fcf_growth_pct": round(config["fcf_growth"] * 100, 2),
                "paydown_ratio_pct": round(config["paydown_ratio"] * 100, 2),
                "refinancing_rate_pct": round(config["roll_rate"] * 100, 2),
            },
            "projections": projections,
        })
    return rows


def build_debt_model(symbol: str, db: Session, years: int = 6) -> dict[str, Any]:
    latest_financial = db.execute(
        select(Financial)
        .where(Financial.ticker == symbol.upper())
        .order_by(desc(Financial.filing_date), desc(Financial.id))
        .limit(1)
    ).scalar_one_or_none()

    # Fetch debt entries across all ingested years (debt schedule is forward-looking, not per-year)
    debt_entries = list(
        db.execute(
            select(DebtSchedule)
            .where(DebtSchedule.ticker == symbol.upper())
            .order_by(DebtSchedule.maturity_year.asc(), DebtSchedule.id.asc())
        ).scalars().all()
    )
    aggregated = _aggregate_debt_rows(debt_entries)

    if latest_financial is None:
        return {
            "symbol": symbol.upper(),
            "debt_maturity": aggregated,
            "de_model": [],
            "latest_capital_structure": None,
        }

    latest_capital_structure = {
        "long_term_debt": _to_float(latest_financial.long_term_debt),
        "total_equity": _to_float(latest_financial.total_equity),
        "free_cash_flow": _to_float(latest_financial.free_cash_flow),
        "citation": {
            "accession_no": latest_financial.accession_no,
            "source_section": latest_financial.source_section or "Item 8",
            "source_page": latest_financial.source_page or 1,
            "filing_date": latest_financial.filing_date.isoformat() if latest_financial.filing_date else None,
        },
    }

    return {
        "symbol": symbol.upper(),
        "debt_maturity": aggregated,
        "de_model": _build_scenario_rows(latest_financial, aggregated),
        "latest_capital_structure": latest_capital_structure,
    }
