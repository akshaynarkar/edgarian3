from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Ticker(Base):
    __tablename__ = "tickers"

    symbol: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str | None] = mapped_column(Text, nullable=True)
    cik: Mapped[str] = mapped_column(String, nullable=False, index=True)
    sector: Mapped[str | None] = mapped_column(Text, nullable=True)
    exchange: Mapped[str | None] = mapped_column(Text, nullable=True)
    price: Mapped[Decimal | None] = mapped_column(Numeric(20, 4), nullable=True)
    price_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_ingested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    financials: Mapped[list[Financial]] = relationship(back_populates="ticker_ref", cascade="all, delete-orphan")
    segments: Mapped[list[Segment]] = relationship(back_populates="ticker_ref", cascade="all, delete-orphan")
    debt_schedules: Mapped[list[DebtSchedule]] = relationship(back_populates="ticker_ref", cascade="all, delete-orphan")
    risk_factors: Mapped[list[RiskFactor]] = relationship(back_populates="ticker_ref", cascade="all, delete-orphan")
    risk_deltas: Mapped[list[RiskDelta]] = relationship(back_populates="ticker_ref", cascade="all, delete-orphan")
    insider_trades: Mapped[list[InsiderTrade]] = relationship(back_populates="ticker_ref", cascade="all, delete-orphan")
    superinvestor_holdings: Mapped[list[SuperInvestorHolding]] = relationship(back_populates="ticker_ref", cascade="all, delete-orphan")
    special_situations: Mapped[list[SpecialSituation]] = relationship(back_populates="ticker_ref")


class Financial(Base):
    __tablename__ = "financials"
    __table_args__ = (UniqueConstraint("ticker", "period", "accession_no", name="uq_financials_ticker_period_accession"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticker: Mapped[str] = mapped_column(ForeignKey("tickers.symbol", ondelete="CASCADE"), index=True)
    period: Mapped[str] = mapped_column(String, nullable=False)
    revenue: Mapped[Decimal | None] = mapped_column(Numeric(20, 4), nullable=True)
    gross_profit: Mapped[Decimal | None] = mapped_column(Numeric(20, 4), nullable=True)
    operating_income: Mapped[Decimal | None] = mapped_column(Numeric(20, 4), nullable=True)
    net_income: Mapped[Decimal | None] = mapped_column(Numeric(20, 4), nullable=True)
    free_cash_flow: Mapped[Decimal | None] = mapped_column(Numeric(20, 4), nullable=True)
    capex: Mapped[Decimal | None] = mapped_column(Numeric(20, 4), nullable=True)
    long_term_debt: Mapped[Decimal | None] = mapped_column(Numeric(20, 4), nullable=True)
    total_equity: Mapped[Decimal | None] = mapped_column(Numeric(20, 4), nullable=True)
    accession_no: Mapped[str] = mapped_column(String, nullable=False, index=True)
    source_section: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    filing_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    ticker_ref: Mapped[Ticker] = relationship(back_populates="financials")


class Segment(Base):
    __tablename__ = "segments"
    __table_args__ = (UniqueConstraint("ticker", "period", "segment_name", "accession_no", name="uq_segments_ticker_period_name_accession"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticker: Mapped[str] = mapped_column(ForeignKey("tickers.symbol", ondelete="CASCADE"), index=True)
    period: Mapped[str] = mapped_column(String, nullable=False)
    segment_name: Mapped[str] = mapped_column(Text, nullable=False)
    revenue: Mapped[Decimal | None] = mapped_column(Numeric(20, 4), nullable=True)
    operating_income: Mapped[Decimal | None] = mapped_column(Numeric(20, 4), nullable=True)
    accession_no: Mapped[str] = mapped_column(String, nullable=False, index=True)
    source_section: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    filing_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    ticker_ref: Mapped[Ticker] = relationship(back_populates="segments")


class DebtSchedule(Base):
    __tablename__ = "debt_schedule"
    __table_args__ = (UniqueConstraint("ticker", "accession_no", "maturity_year", "instrument", name="uq_debt_schedule_accession_year_instrument"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticker: Mapped[str] = mapped_column(ForeignKey("tickers.symbol", ondelete="CASCADE"), index=True)
    maturity_year: Mapped[int] = mapped_column(Integer, nullable=False)
    amount: Mapped[Decimal | None] = mapped_column(Numeric(20, 4), nullable=True)
    instrument: Mapped[str | None] = mapped_column(Text, nullable=True)
    accession_no: Mapped[str] = mapped_column(String, nullable=False, index=True)
    source_section: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    filing_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    ticker_ref: Mapped[Ticker] = relationship(back_populates="debt_schedules")


class RiskFactor(Base):
    __tablename__ = "risk_factors"
    __table_args__ = (UniqueConstraint("ticker", "accession_no", "factor_hash", name="uq_risk_factors_ticker_accession_hash"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticker: Mapped[str] = mapped_column(ForeignKey("tickers.symbol", ondelete="CASCADE"), index=True)
    accession_no: Mapped[str] = mapped_column(String, nullable=False, index=True)
    filing_year: Mapped[int] = mapped_column(Integer, nullable=False)
    factor_text: Mapped[str] = mapped_column(Text, nullable=False)
    factor_hash: Mapped[str] = mapped_column(String, nullable=False)
    source_page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    filing_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    ticker_ref: Mapped[Ticker] = relationship(back_populates="risk_factors")


class RiskDelta(Base):
    __tablename__ = "risk_deltas"
    __table_args__ = (UniqueConstraint("ticker", "filing_year", "delta_type", "accession_no", "factor_text", name="uq_risk_deltas_dedup"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticker: Mapped[str] = mapped_column(ForeignKey("tickers.symbol", ondelete="CASCADE"), index=True)
    filing_year: Mapped[int] = mapped_column(Integer, nullable=False)
    delta_type: Mapped[str] = mapped_column(String, nullable=False)
    factor_text: Mapped[str] = mapped_column(Text, nullable=False)
    prior_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    accession_no: Mapped[str] = mapped_column(String, nullable=False, index=True)
    prior_accession_no: Mapped[str | None] = mapped_column(String, nullable=True)
    source_page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    ticker_ref: Mapped[Ticker] = relationship(back_populates="risk_deltas")


class InsiderTrade(Base):
    __tablename__ = "insider_trades"
    __table_args__ = (UniqueConstraint("ticker", "accession_no", "insider_name", "transaction_date", "transaction_type", "shares", "price_per_share", name="uq_insider_trades_dedup"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticker: Mapped[str] = mapped_column(ForeignKey("tickers.symbol", ondelete="CASCADE"), index=True)
    insider_name: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    transaction_type: Mapped[str] = mapped_column(String, nullable=False)
    shares: Mapped[Decimal | None] = mapped_column(Numeric(20, 4), nullable=True)
    price_per_share: Mapped[Decimal | None] = mapped_column(Numeric(20, 4), nullable=True)
    total_value: Mapped[Decimal | None] = mapped_column(Numeric(20, 4), nullable=True)
    is_10b5_1: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    transaction_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    accession_no: Mapped[str] = mapped_column(String, nullable=False, index=True)
    source_page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    filing_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    ticker_ref: Mapped[Ticker] = relationship(back_populates="insider_trades")


class SuperInvestorHolding(Base):
    __tablename__ = "superinvestor_holdings"
    __table_args__ = (UniqueConstraint("investor_name", "ticker", "period", "accession_no", name="uq_superinvestor_holdings_dedup"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    investor_name: Mapped[str] = mapped_column(Text, nullable=False)
    fund_name: Mapped[str] = mapped_column(Text, nullable=False)
    fund_cik: Mapped[str] = mapped_column(String, nullable=False, index=True)
    ticker: Mapped[str] = mapped_column(ForeignKey("tickers.symbol", ondelete="CASCADE"), index=True)
    period: Mapped[str] = mapped_column(String, nullable=False)
    shares_held: Mapped[Decimal | None] = mapped_column(Numeric(20, 4), nullable=True)
    market_value: Mapped[Decimal | None] = mapped_column(Numeric(20, 4), nullable=True)
    qoq_change: Mapped[str | None] = mapped_column(String, nullable=True)
    qoq_change_pct: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    accession_no: Mapped[str] = mapped_column(String, nullable=False, index=True)
    source_page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    filing_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    ticker_ref: Mapped[Ticker] = relationship(back_populates="superinvestor_holdings")


class SpecialSituation(Base):
    __tablename__ = "special_situations"
    __table_args__ = (UniqueConstraint("accession_no", "ticker", "situation_type", name="uq_special_situations_accession_ticker_type"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticker: Mapped[str | None] = mapped_column(ForeignKey("tickers.symbol", ondelete="SET NULL"), nullable=True, index=True)
    situation_type: Mapped[str] = mapped_column(Text, nullable=False)
    filing_type: Mapped[str] = mapped_column(String, nullable=False)
    color: Mapped[str] = mapped_column(String, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    accession_no: Mapped[str] = mapped_column(String, nullable=False, index=True)
    cik: Mapped[str] = mapped_column(String, nullable=False)
    source_page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    filing_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    ticker_ref: Mapped[Ticker | None] = relationship(back_populates="special_situations")


class FeedEvent(Base):
    __tablename__ = "feed_events"

    accession_no: Mapped[str] = mapped_column(String, primary_key=True)
    form_type: Mapped[str] = mapped_column(String, nullable=False)
    company_name: Mapped[str] = mapped_column(Text, nullable=False)
    ticker: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    cik: Mapped[str] = mapped_column(String, nullable=False, index=True)
    signal_color: Mapped[str] = mapped_column(String, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    filing_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    priority_score: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    google_id: Mapped[str | None] = mapped_column(Text, nullable=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    notes: Mapped[list[Note]] = relationship(back_populates="user", cascade="all, delete-orphan")
    highlights: Mapped[list[Highlight]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Note(Base):
    __tablename__ = "notes"
    __table_args__ = (UniqueConstraint("user_id", "ticker", name="uq_notes_user_ticker"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    ticker: Mapped[str] = mapped_column(ForeignKey("tickers.symbol", ondelete="CASCADE"), index=True)
    note_text: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    user: Mapped[User] = relationship(back_populates="notes")


class Highlight(Base):
    __tablename__ = "highlights"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    accession_no: Mapped[str] = mapped_column(String, nullable=False, index=True)
    page: Mapped[int] = mapped_column(Integer, nullable=False)
    coords: Mapped[dict[str, Any] | list[Any] | None] = mapped_column(JSONB, nullable=True)
    color: Mapped[str | None] = mapped_column(String, nullable=True)
    note_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    user: Mapped[User] = relationship(back_populates="highlights")
