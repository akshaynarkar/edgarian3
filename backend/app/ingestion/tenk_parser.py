from __future__ import annotations

import logging
import re
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Iterable

import pandas as pd
from edgar import Company, set_identity
from edgar.xbrl import XBRL
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.database import SessionLocal
from app.db.models import DebtSchedule, Financial, Segment, Ticker
from app.ingestion.ticker_ingest import ticker_ingest
from app.utils.date_utils import to_date

logger = logging.getLogger(__name__)
settings = get_settings()

FACT_ALIASES: dict[str, list[str]] = {
    "revenue": ["Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax", "SalesRevenueNet"],
    "gross_profit": ["GrossProfit"],
    "operating_income": ["OperatingIncomeLoss"],
    "net_income": ["NetIncomeLoss", "ProfitLoss"],
    "operating_cash_flow": ["NetCashProvidedByUsedInOperatingActivities", "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations"],
    "capex": ["PaymentsToAcquirePropertyPlantAndEquipment", "CapitalExpendituresIncurredButNotYetPaid"],
    "long_term_debt": ["LongTermDebtNoncurrent", "LongTermDebt"],
    "total_equity": ["StockholdersEquity", "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"],
}

SEGMENT_CONCEPTS = [
    "RevenueFromContractWithCustomerExcludingAssessedTax",
    "Revenues",
    "SegmentReportingInformation",
]

DEBT_CONCEPTS = [
    "LongTermDebtMaturitiesRepaymentsOfPrincipalInNextTwelveMonths",
    "LongTermDebtMaturitiesRepaymentsOfPrincipalInYearTwo",
    "LongTermDebtMaturitiesRepaymentsOfPrincipalInYearThree",
    "LongTermDebtMaturitiesRepaymentsOfPrincipalInYearFour",
    "LongTermDebtMaturitiesRepaymentsOfPrincipalInYearFive",
    "LongTermDebtMaturitiesRepaymentsOfPrincipalAfterYearFive",
]


def _to_decimal(value: Any) -> Decimal | None:
    if value in (None, "", "NaN"):
        return None
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value).replace(",", ""))
    except (InvalidOperation, ValueError, TypeError):
        return None


def _get_facts_df(xbrl: XBRL, concept_name: str) -> pd.DataFrame:
    try:
        df = xbrl.facts.get_facts_by_concept(concept_name)
        if isinstance(df, pd.DataFrame) and not df.empty:
            return df
    except Exception as e:
        logger.debug("get_facts_by_concept(%s) failed: %s", concept_name, e)
    return pd.DataFrame()


def _pick_latest_value(xbrl: XBRL, aliases: Iterable[str]) -> Decimal | None:
    for alias in aliases:
        df = _get_facts_df(xbrl, alias)
        if df.empty:
            continue
        if "is_dimensioned" in df.columns:
            df = df[df["is_dimensioned"] == False]  # noqa: E712
        if "fiscal_period" in df.columns:
            df = df[df["fiscal_period"] == "FY"]
        if df.empty:
            continue
        if "period_end" in df.columns:
            df = df.sort_values("period_end", ascending=False)
        for col in ("numeric_value", "value", "fact_value"):
            if col not in df.columns:
                continue
            series = df[col].dropna()
            if not series.empty:
                value = _to_decimal(series.iloc[0])
                if value is not None:
                    return value
            break
    return None


def _extract_period_label(filing: Any) -> str:
    filing_date = to_date(getattr(filing, "filing_date", None))
    report_date = to_date(getattr(filing, "period_of_report", None)) or filing_date
    if report_date is None:
        return f"FY{datetime.now(timezone.utc).year}"
    return f"FY{report_date.year}"


def _extract_accession_no(filing: Any) -> str:
    return str(getattr(filing, "accession_no", None) or getattr(filing, "accession_number", ""))


def _is_xbrl_context_id(value: str) -> bool:
    return bool(re.match(r"^[a-zA-Z]{1,3}-\d+$", value.strip()))


def _extract_segments(xbrl: XBRL, ticker: str, accession_no: str, filing_date: date | None, period: str) -> list[Segment]:
    segment_rows: list[Segment] = []
    seen: set[tuple[str, str, str]] = set()

    for concept_name in SEGMENT_CONCEPTS:
        df = _get_facts_df(xbrl, concept_name)
        if df.empty:
            continue
        if "is_dimensioned" in df.columns:
            df = df[df["is_dimensioned"] == True]  # noqa: E712
        if df.empty:
            continue
        if "fiscal_period" in df.columns:
            fy_df = df[df["fiscal_period"] == "FY"]
            if not fy_df.empty:
                df = fy_df
        if "period_end" in df.columns:
            df = df.sort_values("period_end", ascending=False)
            latest_period = df["period_end"].iloc[0]
            df = df[df["period_end"] == latest_period]

        for _, row in df.iterrows():
            numeric_value = _to_decimal(row.get("numeric_value"))
            if numeric_value is None or numeric_value <= 0:
                continue

            segment_name = None
            for col in ("label", "segment_name", "dimension_value", "concept"):
                val = row.get(col)
                if not val or str(val) in ("", "nan"):
                    continue
                raw = str(val).strip()
                if _is_xbrl_context_id(raw):
                    continue
                raw = re.sub(r"Member$", "", raw)
                raw = re.sub(r"Segment$", "", raw)
                raw = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", raw).strip()
                if raw and raw.lower() not in ("nan", concept_name.lower()):
                    segment_name = raw
                    break

            if segment_name is None:
                val = row.get("context_ref")
                if val and str(val) not in ("", "nan"):
                    raw = str(val).strip()
                    if not _is_xbrl_context_id(raw):
                        raw = re.sub(r"Member$", "", raw)
                        raw = re.sub(r"Segment$", "", raw)
                        raw = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", raw).strip()
                        if raw:
                            segment_name = raw

            if segment_name is None:
                continue

            dedup_key = (ticker, period, segment_name)
            if dedup_key in seen:
                continue
            seen.add(dedup_key)

            segment_rows.append(Segment(
                ticker=ticker, period=period, segment_name=segment_name,
                revenue=numeric_value, operating_income=None,
                accession_no=accession_no, source_section="Item 8",
                source_page=None, filing_date=filing_date,
            ))
    return segment_rows


def _extract_debt_schedule(xbrl: XBRL, ticker: str, accession_no: str, filing_date: date | None) -> list[DebtSchedule]:
    records: list[DebtSchedule] = []
    base_year = filing_date.year if filing_date else datetime.now(timezone.utc).year
    mapping = {
        "LongTermDebtMaturitiesRepaymentsOfPrincipalInNextTwelveMonths": (base_year + 1, "Debt due within 12 months"),
        "LongTermDebtMaturitiesRepaymentsOfPrincipalInYearTwo": (base_year + 2, "Debt due in year two"),
        "LongTermDebtMaturitiesRepaymentsOfPrincipalInYearThree": (base_year + 3, "Debt due in year three"),
        "LongTermDebtMaturitiesRepaymentsOfPrincipalInYearFour": (base_year + 4, "Debt due in year four"),
        "LongTermDebtMaturitiesRepaymentsOfPrincipalInYearFive": (base_year + 5, "Debt due in year five"),
        "LongTermDebtMaturitiesRepaymentsOfPrincipalAfterYearFive": (base_year + 6, "Debt due after year five"),
    }
    for concept_name in DEBT_CONCEPTS:
        value = _pick_latest_value(xbrl, [concept_name])
        if value is None:
            continue
        maturity_year, instrument = mapping[concept_name]
        records.append(DebtSchedule(
            ticker=ticker, maturity_year=maturity_year, amount=value,
            instrument=instrument, accession_no=accession_no,
            source_section="Note 6", source_page=None, filing_date=filing_date,
        ))
    return records


def _parse_single_filing(filing: Any, symbol: str, db: Session) -> dict[str, Any]:
    """Parse one filing object and write to DB."""
    xbrl = XBRL.from_filing(filing)
    accession_no = _extract_accession_no(filing)
    filing_date = to_date(getattr(filing, "filing_date", None))
    period = _extract_period_label(filing)

    revenue = _pick_latest_value(xbrl, FACT_ALIASES["revenue"])
    gross_profit = _pick_latest_value(xbrl, FACT_ALIASES["gross_profit"])
    operating_income = _pick_latest_value(xbrl, FACT_ALIASES["operating_income"])
    net_income = _pick_latest_value(xbrl, FACT_ALIASES["net_income"])
    capex = _pick_latest_value(xbrl, FACT_ALIASES["capex"])
    operating_cash_flow = _pick_latest_value(xbrl, FACT_ALIASES["operating_cash_flow"])
    long_term_debt = _pick_latest_value(xbrl, FACT_ALIASES["long_term_debt"])
    total_equity = _pick_latest_value(xbrl, FACT_ALIASES["total_equity"])
    free_cash_flow = (
        operating_cash_flow - capex
        if operating_cash_flow is not None and capex is not None else None
    )

    db.execute(delete(Financial).where(Financial.ticker == symbol, Financial.accession_no == accession_no))
    db.execute(delete(Segment).where(Segment.ticker == symbol, Segment.accession_no == accession_no))
    db.execute(delete(DebtSchedule).where(DebtSchedule.ticker == symbol, DebtSchedule.accession_no == accession_no))

    db.add(Financial(
        ticker=symbol, period=period, revenue=revenue, gross_profit=gross_profit,
        operating_income=operating_income, net_income=net_income,
        free_cash_flow=free_cash_flow, capex=capex,
        long_term_debt=long_term_debt, total_equity=total_equity,
        accession_no=accession_no, source_section="Item 8",
        source_page=None, filing_date=filing_date,
        computed_at=datetime.now(timezone.utc),
    ))

    segments = _extract_segments(xbrl=xbrl, ticker=symbol, accession_no=accession_no, filing_date=filing_date, period=period)
    debts = _extract_debt_schedule(xbrl=xbrl, ticker=symbol, accession_no=accession_no, filing_date=filing_date)
    for item in segments + debts:
        db.add(item)

    logger.info("Parsed %s period=%s segments=%d debts=%d", accession_no, period, len(segments), len(debts))
    return {"accession_no": accession_no, "period": period, "segments": len(segments), "debts": len(debts)}


def _iter_filings(filings_obj: Any, n: int):
    """
    Safely iterate up to n filings from edgartools 5.x EntityFilings.
    Tries index access [i] first; falls back to iterating the object directly.
    """
    collected = []
    # Strategy 1: index access (works for EntityFilings in most versions)
    try:
        for i in range(n):
            try:
                filing = filings_obj[i]
                collected.append(filing)
            except (IndexError, KeyError):
                break
        if collected:
            return collected
    except Exception:
        pass

    # Strategy 2: direct iteration
    try:
        for i, filing in enumerate(filings_obj):
            if i >= n:
                break
            collected.append(filing)
        if collected:
            return collected
    except Exception:
        pass

    # Strategy 3: .filings attribute (some versions wrap results)
    try:
        inner = getattr(filings_obj, "filings", None) or getattr(filings_obj, "_filings", None)
        if inner is not None:
            for i, filing in enumerate(inner):
                if i >= n:
                    break
                collected.append(filing)
    except Exception:
        pass

    return collected


def tenk_parser(symbol: str, db: Session | None = None) -> dict[str, Any]:
    """Parse latest 10-K only."""
    return tenk_parser_multi(symbol, n=1, db=db)


def tenk_parser_multi(symbol: str, n: int = 6, db: Session | None = None) -> dict[str, Any]:
    """Parse the last N 10-K filings for a symbol and write all to DB."""
    symbol = symbol.upper().strip()
    if not symbol:
        raise ValueError("symbol is required")
    n = max(1, min(n, 20))

    own_session = db is None
    if db is None:
        db = SessionLocal()

    try:
        ticker = db.scalar(select(Ticker).where(Ticker.symbol == symbol))
        if ticker is None:
            ticker = ticker_ingest(symbol, db=db)

        set_identity(settings.sec_user_agent)
        company = Company(ticker.cik)
        filings_obj = company.get_filings(form="10-K")

        # edgartools 5.x: .latest(1) returns a single Filing; .latest(n>1) returns EntityFilings
        # Use _iter_filings to handle both cases safely
        all_filings = _iter_filings(filings_obj, n)

        if not all_filings:
            logger.warning("No filings found for %s", symbol)
            return {"ticker": symbol, "filings_parsed": 0, "results": []}

        results = []
        for filing in all_filings:
            try:
                result = _parse_single_filing(filing, symbol, db)
                results.append(result)
            except Exception as e:
                logger.warning("Skipping filing for %s: %s", symbol, e)

        ticker.last_ingested_at = datetime.now(timezone.utc)
        db.commit()

        return {"ticker": symbol, "filings_parsed": len(results), "results": results}

    except Exception as e:
        logger.exception("Failed tenk_parser_multi for %s: %s", symbol, e)
        db.rollback()
        raise
    finally:
        if own_session:
            db.close()
