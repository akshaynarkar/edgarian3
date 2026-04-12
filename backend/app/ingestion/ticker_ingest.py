from __future__ import annotations

import logging
from datetime import datetime, timezone

from edgar import Company, set_identity
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.database import SessionLocal
from app.db.models import Ticker

logger = logging.getLogger(__name__)
settings = get_settings()


def _safe_attr(obj: object, *names: str) -> str | None:
    for name in names:
        value = getattr(obj, name, None)
        if value not in (None, ""):
            return str(value)
    return None


def ticker_ingest(symbol: str, db: Session | None = None) -> Ticker:
    symbol = symbol.upper().strip()
    if not symbol:
        raise ValueError("symbol is required")

    own_session = db is None
    if db is None:
        db = SessionLocal()

    try:
        set_identity(settings.sec_user_agent)
        company = Company(symbol)

        ticker = Ticker(
            symbol=symbol,
            name=_safe_attr(company, "name", "company_name"),
            cik=_safe_attr(company, "cik") or symbol,
            sector=_safe_attr(company, "sic_description", "sector", "industry"),
            exchange=_safe_attr(company, "exchange"),
            last_ingested_at=datetime.now(timezone.utc),
        )

        db.execute(delete(Ticker).where(Ticker.symbol == symbol))
        db.add(ticker)
        db.commit()
        db.refresh(ticker)
        logger.info("Ticker ingested for %s with CIK %s", symbol, ticker.cik)
        return ticker
    except Exception as e:
        logger.exception("Failed to ingest ticker %s: %s", symbol, e)
        if own_session:
            db.rollback()
        raise
    finally:
        if own_session:
            db.close()
