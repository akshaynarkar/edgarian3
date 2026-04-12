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


def _safe_get_concept(xbrl: XBRL, concept_name: str) -> Any:
    try:
        return xbrl.facts.get_concept(concept_name)
    except Exception:
        try:
            return xbrl.facts.by_concept(concept_name)
        except Exception:
            return None


def _concept_to_dataframe(concept_obj: Any) -> pd.DataFrame:
    if concept_obj is None:
        return pd.DataFrame()
    if isinstance(concept_obj, pd.DataFrame):
        return concept_obj.copy()
    for method_name in ("to_dataframe", "to_pandas"):
        method = getattr(concept_obj, method_name, None)
        if callable(method):
            try:
                df = method()
                if isinstance(df, pd.DataFrame):
                    return df
            except Exception:
                continue
    execute = getattr(concept_obj, "execute", None)
    if callable(execute):
        try:
            rows = execute()
            if isinstance(rows, list):
                return pd.DataFrame(rows)
        except Exception:
            pass
    if isinstance(concept_obj, list):
        return pd.DataFrame(concept_obj)
    return pd.DataFrame()


def _pick_latest_value(xbrl: XBRL, aliases: Iterable[str]) -> Decimal | None:
    for alias in aliases:
        df = _concept_to_dataframe(_safe_get_concept(xbrl, alias))
        if df.empty:
            continue
        value_column = next((c for c in ["value", "numeric_value", "fact_value"] if c in df.columns), None)
        if value_column is None:
            continue
        sort_column = next((c for c in ["end_date", "period_end", "instant", "date"] if c in df.columns), None)
        if sort_column:
            df = df.sort_values(by=sort_column)
        series = df[value_column].dropna()
        if not series.empty:
            value = _to_decimal(series.iloc[-1])
            if value is not None:
                return value
    return None


def _extract_period_label(filing: Any) -> str:
    filing_date = to_date(getattr(filing, "filing_date", None))
    report_date = to_date(getattr(filing, "period_of_report", None)) or filing_date
    if report_date is None:
        return f"FY{datetime.now(timezone.utc).year}"
    return f"FY{report_date.year}"


def _extract_accession_no(filing: Any) -> str:
    return str(getattr(filing, "accession_no", None) or getattr(filing, "accession_number", ""))


def _extract_source_page(rows: list[dict[str, Any]]) -> int | None:
    for row in rows:
        for key in ("page", "source_page"):
            raw = row.get(key)
            if raw not in (None, ""):
                try:
                    return int(raw)
                except (TypeError, ValueError):
                    continue
    return None


def _normalize_record(row: dict[str, Any]) -> dict[str, Any]:
    lowered = {str(k).lower(): v for k, v in row.items()}
    if "dimensions" in lowered and isinstance(lowered["dimensions"], dict):
        for key, value in lowered["dimensions"].items():
            lowered[str(key).lower()] = value
    return lowered


def _extract_segments(xbrl: XBRL, ticker: str, accession_no: str, filing_date: date | None, period: str) -> list[Segment]:
    segment_rows: list[Segment] = []
    seen: set[tuple[str, str, str]] = set()
    for concept_name in SEGMENT_CONCEPTS:
        df = _concept_to_dataframe(_safe_get_concept(xbrl, concept_name))
        if df.empty:
            continue
        for row in df.to_dict(orient="records"):
            normalized = _normalize_record(row)
            member = next(
                (
                    str(value)
                    for key, value in normalized.items()
                    if value not in (None, "") and ("segment" in key or "member" in key or "axis" in key)
                ),
                None,
            )
            if member is None:
                continue
            value = _to_decimal(normalized.get("value") or normalized.get("numeric_value") or normalized.get("fact_value"))
            if value is None:
                continue
            clean_member = re.sub(r"Member$", "", member)
            clean_member = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", clean_member).strip()
            dedup_key = (ticker, period, clean_member)
            if dedup_key in seen:
                continue
            seen.add(dedup_key)
            segment_rows.append(
                Segment(
                    ticker=ticker,
                    period=period,
                    segment_name=clean_member,
                    revenue=value,
                    operating_income=None,
                    accession_no=accession_no,
                    source_section="Item 8",
                    source_page=_extract_source_page([normalized]),
                    filing_date=filing_date,
                )
            )
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
        records.append(
            DebtSchedule(
                ticker=ticker,
                maturity_year=maturity_year,
                amount=value,
                instrument=instrument,
                accession_no=accession_no,
                source_section="Note 6",
                source_page=None,
                filing_date=filing_date,
            )
        )
    return records


def tenk_parser(symbol: str, db: Session | None = None) -> dict[str, int | str]:
    symbol = symbol.upper().strip()
    if not symbol:
        raise ValueError("symbol is required")

    own_session = db is None
    if db is None:
        db = SessionLocal()

    try:
        ticker = db.scalar(select(Ticker).where(Ticker.symbol == symbol))
        if ticker is None:
            ticker = ticker_ingest(symbol, db=db)

        set_identity(settings.sec_user_agent)
        company = Company(ticker.cik)
        filings = company.get_filings(form="10-K")
        filing = filings.latest(1)
        filing = filing[0] if isinstance(filing, list) else filing
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
        free_cash_flow = operating_cash_flow - capex if operating_cash_flow is not None and capex is not None else None

        db.execute(delete(Financial).where(Financial.ticker == symbol, Financial.accession_no == accession_no))
        db.execute(delete(Segment).where(Segment.ticker == symbol, Segment.accession_no == accession_no))
        db.execute(delete(DebtSchedule).where(DebtSchedule.ticker == symbol, DebtSchedule.accession_no == accession_no))

        financial_row = Financial(
            ticker=symbol,
            period=period,
            revenue=revenue,
            gross_profit=gross_profit,
            operating_income=operating_income,
            net_income=net_income,
            free_cash_flow=free_cash_flow,
            capex=capex,
            long_term_debt=long_term_debt,
            total_equity=total_equity,
            accession_no=accession_no,
            source_section="Item 8",
            source_page=None,
            filing_date=filing_date,
            computed_at=datetime.now(timezone.utc),
        )
        db.add(financial_row)

        segments = _extract_segments(xbrl=xbrl, ticker=symbol, accession_no=accession_no, filing_date=filing_date, period=period)
        debts = _extract_debt_schedule(xbrl=xbrl, ticker=symbol, accession_no=accession_no, filing_date=filing_date)

        for item in segments + debts:
            db.add(item)

        ticker.last_ingested_at = datetime.now(timezone.utc)
        db.commit()

        result = {
            "ticker": symbol,
            "accession_no": accession_no,
            "financials_written": 1,
            "segments_written": len(segments),
            "debt_schedule_written": len(debts),
        }
        logger.info("10-K parsed for %s: %s", symbol, result)
        return result
    except Exception as e:
        logger.exception("Failed to parse 10-K for %s: %s", symbol, e)
        db.rollback()
        raise
    finally:
        if own_session:
            db.close()
