from __future__ import annotations

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from edgar import Company, set_identity
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.database import SessionLocal
from app.db.models import InsiderTrade, Ticker
from app.ingestion.ticker_ingest import ticker_ingest
from app.utils.date_utils import to_date

logger = logging.getLogger(__name__)
settings = get_settings()


TRANSACTION_CODE_MAP = {
    "P": "buy",
    "S": "sell",
}


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _decimal(value: Any) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value).replace(",", ""))
    except Exception:
        return None


def _extract_owner_name(form4: Any) -> str:
    reporting_owner = getattr(form4, "reporting_owner", None)
    if isinstance(reporting_owner, list):
        first_owner = reporting_owner[0] if reporting_owner else None
        if first_owner is not None:
            return str(getattr(first_owner, "name", None) or getattr(first_owner, "owner_name", "Unknown Insider"))
    return str(
        getattr(form4, "reporting_owner_name", None)
        or getattr(reporting_owner, "name", None)
        or "Unknown Insider"
    )


def _extract_owner_title(form4: Any) -> str | None:
    relationship = getattr(form4, "reporting_owner_relationship", None)
    if relationship not in (None, ""):
        return str(relationship)
    reporting_owner = getattr(form4, "reporting_owner", None)
    owners = reporting_owner if isinstance(reporting_owner, list) else [reporting_owner]
    for owner in owners:
        if owner is None:
            continue
        for field in ("officer_title", "title", "relationship"):
            value = getattr(owner, field, None)
            if value not in (None, ""):
                return str(value)
    return None


def _extract_transactions(form4: Any) -> list[Any]:
    transactions = _as_list(getattr(form4, "transactions", None))
    if transactions:
        return transactions
    non_derivative_table = getattr(form4, "non_derivative_table", None)
    if non_derivative_table is None:
        return []
    for attr in ("transactions", "non_derivative_transactions"):
        values = _as_list(getattr(non_derivative_table, attr, None))
        if values:
            return values
    return []


def form4_parser(symbol: str, db: Session | None = None, max_filings: int = 25) -> dict[str, int | str]:
    symbol = symbol.upper().strip()
    if not symbol:
        raise ValueError("symbol is required")

    own_session = db is None
    if db is None:
        db = SessionLocal()

    inserted = 0
    try:
        ticker = db.scalar(select(Ticker).where(Ticker.symbol == symbol))
        if ticker is None:
            ticker = ticker_ingest(symbol, db=db)

        set_identity(settings.sec_user_agent)
        company = Company(ticker.cik)
        filings = company.get_filings(form="4")
        filing_list = filings.head(max_filings) if hasattr(filings, "head") else filings[:max_filings]

        for filing in filing_list:
            accession_no = str(getattr(filing, "accession_no", None) or getattr(filing, "accession_number", ""))
            if not accession_no:
                continue

            db.execute(delete(InsiderTrade).where(InsiderTrade.ticker == symbol, InsiderTrade.accession_no == accession_no))

            form4 = filing.obj()
            insider_name = _extract_owner_name(form4)
            title = _extract_owner_title(form4)
            filing_date = to_date(getattr(form4, "filing_date", None) or getattr(filing, "filing_date", None))

            for txn in _extract_transactions(form4):
                code = str(getattr(txn, "transaction_code", None) or getattr(txn, "code", "")).upper()
                transaction_type = TRANSACTION_CODE_MAP.get(code)
                if transaction_type is None:
                    continue

                shares = _decimal(getattr(txn, "shares", None) or getattr(txn, "transaction_shares", None))
                price = _decimal(getattr(txn, "price_per_share", None) or getattr(txn, "price", None))
                is_10b5_1 = bool(
                    getattr(txn, "is_10b5_1", False)
                    or getattr(txn, "trading_plan_10b5_1", False)
                    or getattr(form4, "is_10b5_1", False)
                )
                transaction_date = to_date(getattr(txn, "transaction_date", None) or getattr(txn, "date", None))
                total_value = (shares * price) if shares is not None and price is not None else None

                db.add(
                    InsiderTrade(
                        ticker=symbol,
                        insider_name=insider_name,
                        title=title,
                        transaction_type=transaction_type,
                        shares=shares,
                        price_per_share=price,
                        total_value=total_value,
                        is_10b5_1=is_10b5_1,
                        transaction_date=transaction_date,
                        accession_no=accession_no,
                        source_page=None,
                        filing_date=filing_date,
                    )
                )
                inserted += 1

        ticker.last_ingested_at = datetime.now(timezone.utc)
        db.commit()
        result = {"ticker": symbol, "rows_written": inserted}
        logger.info("Form 4 parsed for %s: %s", symbol, result)
        return result
    except Exception as e:
        logger.exception("Failed to parse Form 4 for %s: %s", symbol, e)
        db.rollback()
        raise
    finally:
        if own_session:
            db.close()
