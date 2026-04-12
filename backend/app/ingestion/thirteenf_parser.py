from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

import pandas as pd
from edgar import Company, set_identity
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.database import SessionLocal
from app.db.models import SuperInvestorHolding
from app.utils.date_utils import to_date

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass(frozen=True)
class SuperInvestor:
    investor_name: str
    fund_name: str
    fund_cik: str


SUPER_INVESTORS: list[SuperInvestor] = [
    SuperInvestor("Warren Buffett", "Berkshire Hathaway", "0001067983"),
    SuperInvestor("Bill Ackman", "Pershing Square", "0001336528"),
    SuperInvestor("Michael Burry", "Scion Asset Mgmt", "0001649339"),
    SuperInvestor("David Einhorn", "Greenlight Capital", "0001079114"),
    SuperInvestor("Seth Klarman", "Baupost Group", "0001061768"),
    SuperInvestor("Howard Marks", "Oaktree Capital", "0001403528"),
    SuperInvestor("Mohnish Pabrai", "Pabrai Funds", "0001173334"),
    SuperInvestor("Guy Spier", "Aquamarine Fund", "0001159159"),
    SuperInvestor("Joel Greenblatt", "Gotham Asset Mgmt", "0001512093"),
    SuperInvestor("Chris Hohn", "TCI Fund Management", "0001343816"),
    SuperInvestor("Francisco Garcia Parames", "Cobas Asset Mgmt", "0001705931"),
    SuperInvestor("Li Lu", "Himalaya Capital", "0001709323"),
    SuperInvestor("David Tepper", "Appaloosa Mgmt", "0001006438"),
    SuperInvestor("Bruce Berkowitz", "Fairholme Fund", "0001056831"),
    SuperInvestor("Prem Watsa", "Fairfax Financial", "0001042046"),
]


def _decimal(value: Any) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value).replace(",", ""))
    except Exception:
        return None


def _to_dataframe(value: Any) -> pd.DataFrame:
    if isinstance(value, pd.DataFrame):
        return value.copy()
    if hasattr(value, "to_dataframe"):
        try:
            df = value.to_dataframe()
            if isinstance(df, pd.DataFrame):
                return df
        except Exception:
            return pd.DataFrame()
    if isinstance(value, list):
        return pd.DataFrame(value)
    return pd.DataFrame()


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    copy = df.copy()
    copy.columns = [str(col).strip() for col in copy.columns]
    return copy


def _period_label(report_period: Any) -> str:
    report_date = to_date(report_period)
    if report_date is None:
        return "Unknown"
    quarter = ((report_date.month - 1) // 3) + 1
    return f"Q{quarter} {report_date.year}"


def _qoq_change(current_shares: Decimal | None, previous_shares: Decimal | None) -> tuple[str, Decimal | None]:
    if current_shares is None:
        return "unknown", None
    if previous_shares in (None, Decimal("0")):
        return "new", None
    delta = current_shares - previous_shares
    pct = (delta / previous_shares) * Decimal("100")
    if delta > 0:
        return "added", pct
    if delta < 0:
        return "reduced", pct
    return "unchanged", Decimal("0")


def thirteenf_parser(db: Session | None = None) -> dict[str, int]:
    own_session = db is None
    if db is None:
        db = SessionLocal()

    total_rows = 0
    try:
        for investor in SUPER_INVESTORS:
            set_identity(settings.sec_user_agent)
            company = Company(investor.fund_cik)
            filings = company.get_filings(form="13F-HR")
            filing = filings.latest(1)
            filing = filing[0] if isinstance(filing, list) else filing
            report = filing.obj()

            if hasattr(report, "has_infotable") and callable(report.has_infotable) and not report.has_infotable():
                continue

            holdings = _normalize_columns(_to_dataframe(getattr(report, "holdings", pd.DataFrame())))
            previous_report = report.previous_holding_report() if hasattr(report, "previous_holding_report") else None
            previous_holdings = _normalize_columns(_to_dataframe(getattr(previous_report, "holdings", pd.DataFrame())))
            previous_map: dict[str, Decimal | None] = {}
            if not previous_holdings.empty and "Ticker" in previous_holdings.columns:
                for _, row in previous_holdings.iterrows():
                    ticker = str(row.get("Ticker", "")).upper().strip()
                    if ticker:
                        previous_map[ticker] = _decimal(row.get("Shares") or row.get("SharesPrnAmount") or row.get("Shares Held"))

            accession_no = str(getattr(report, "accession_number", None) or getattr(filing, "accession_number", ""))
            period = _period_label(getattr(report, "report_period", None))
            filing_date = to_date(getattr(report, "filing_date", None) or getattr(filing, "filing_date", None))

            db.execute(
                delete(SuperInvestorHolding).where(
                    SuperInvestorHolding.investor_name == investor.investor_name,
                    SuperInvestorHolding.accession_no == accession_no,
                )
            )

            for _, row in holdings.iterrows():
                ticker = str(row.get("Ticker", "")).upper().strip()
                if not ticker:
                    continue
                shares = _decimal(row.get("Shares") or row.get("SharesPrnAmount") or row.get("Shares Held"))
                market_value = _decimal(row.get("Value"))
                if market_value is not None:
                    market_value *= Decimal("1000")
                change, change_pct = _qoq_change(shares, previous_map.get(ticker))
                db.add(
                    SuperInvestorHolding(
                        investor_name=investor.investor_name,
                        fund_name=investor.fund_name,
                        fund_cik=investor.fund_cik,
                        ticker=ticker,
                        period=period,
                        shares_held=shares,
                        market_value=market_value,
                        qoq_change=change,
                        qoq_change_pct=change_pct,
                        accession_no=accession_no,
                        source_page=None,
                        filing_date=filing_date,
                    )
                )
                total_rows += 1

        db.commit()
        result = {"rows_written": total_rows, "investors_processed": len(SUPER_INVESTORS)}
        logger.info("13F parse complete: %s", result)
        return result
    except Exception as e:
        logger.exception("Failed to parse 13F holdings: %s", e)
        db.rollback()
        raise
    finally:
        if own_session:
            db.close()
