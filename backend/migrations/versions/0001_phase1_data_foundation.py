"""phase1 data foundation

Revision ID: 0001_phase1
Revises: None
Create Date: 2026-04-11 00:00:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0001_phase1"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "feed_events",
        sa.Column("accession_no", sa.String(), primary_key=True),
        sa.Column("form_type", sa.String(), nullable=False),
        sa.Column("company_name", sa.Text(), nullable=False),
        sa.Column("ticker", sa.String(), nullable=True),
        sa.Column("cik", sa.String(), nullable=False),
        sa.Column("signal_color", sa.String(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("filing_date", sa.Date(), nullable=True),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("priority_score", sa.Numeric(10, 4), nullable=True),
    )
    op.create_index("ix_feed_events_ticker", "feed_events", ["ticker"], unique=False)
    op.create_index("ix_feed_events_cik", "feed_events", ["cik"], unique=False)

    op.create_table(
        "tickers",
        sa.Column("symbol", sa.String(), primary_key=True),
        sa.Column("name", sa.Text(), nullable=True),
        sa.Column("cik", sa.String(), nullable=False),
        sa.Column("sector", sa.Text(), nullable=True),
        sa.Column("exchange", sa.Text(), nullable=True),
        sa.Column("price", sa.Numeric(20, 4), nullable=True),
        sa.Column("price_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_ingested_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_tickers_cik", "tickers", ["cik"], unique=False)

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("email", sa.Text(), nullable=False, unique=True),
        sa.Column("google_id", sa.Text(), nullable=True, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "financials",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("ticker", sa.String(), sa.ForeignKey("tickers.symbol", ondelete="CASCADE"), nullable=False),
        sa.Column("period", sa.String(), nullable=False),
        sa.Column("revenue", sa.Numeric(20, 4), nullable=True),
        sa.Column("gross_profit", sa.Numeric(20, 4), nullable=True),
        sa.Column("operating_income", sa.Numeric(20, 4), nullable=True),
        sa.Column("net_income", sa.Numeric(20, 4), nullable=True),
        sa.Column("free_cash_flow", sa.Numeric(20, 4), nullable=True),
        sa.Column("capex", sa.Numeric(20, 4), nullable=True),
        sa.Column("long_term_debt", sa.Numeric(20, 4), nullable=True),
        sa.Column("total_equity", sa.Numeric(20, 4), nullable=True),
        sa.Column("accession_no", sa.String(), nullable=False),
        sa.Column("source_section", sa.Text(), nullable=True),
        sa.Column("source_page", sa.Integer(), nullable=True),
        sa.Column("filing_date", sa.Date(), nullable=True),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("ticker", "period", "accession_no", name="uq_financials_ticker_period_accession"),
    )
    op.create_index("ix_financials_ticker", "financials", ["ticker"], unique=False)
    op.create_index("ix_financials_accession_no", "financials", ["accession_no"], unique=False)

    op.create_table(
        "segments",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("ticker", sa.String(), sa.ForeignKey("tickers.symbol", ondelete="CASCADE"), nullable=False),
        sa.Column("period", sa.String(), nullable=False),
        sa.Column("segment_name", sa.Text(), nullable=False),
        sa.Column("revenue", sa.Numeric(20, 4), nullable=True),
        sa.Column("operating_income", sa.Numeric(20, 4), nullable=True),
        sa.Column("accession_no", sa.String(), nullable=False),
        sa.Column("source_section", sa.Text(), nullable=True),
        sa.Column("source_page", sa.Integer(), nullable=True),
        sa.Column("filing_date", sa.Date(), nullable=True),
        sa.UniqueConstraint("ticker", "period", "segment_name", "accession_no", name="uq_segments_ticker_period_name_accession"),
    )
    op.create_index("ix_segments_ticker", "segments", ["ticker"], unique=False)
    op.create_index("ix_segments_accession_no", "segments", ["accession_no"], unique=False)

    op.create_table(
        "debt_schedule",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("ticker", sa.String(), sa.ForeignKey("tickers.symbol", ondelete="CASCADE"), nullable=False),
        sa.Column("maturity_year", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Numeric(20, 4), nullable=True),
        sa.Column("instrument", sa.Text(), nullable=True),
        sa.Column("accession_no", sa.String(), nullable=False),
        sa.Column("source_section", sa.Text(), nullable=True),
        sa.Column("source_page", sa.Integer(), nullable=True),
        sa.Column("filing_date", sa.Date(), nullable=True),
        sa.UniqueConstraint("ticker", "accession_no", "maturity_year", "instrument", name="uq_debt_schedule_accession_year_instrument"),
    )
    op.create_index("ix_debt_schedule_ticker", "debt_schedule", ["ticker"], unique=False)
    op.create_index("ix_debt_schedule_accession_no", "debt_schedule", ["accession_no"], unique=False)

    op.create_table(
        "risk_factors",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("ticker", sa.String(), sa.ForeignKey("tickers.symbol", ondelete="CASCADE"), nullable=False),
        sa.Column("accession_no", sa.String(), nullable=False),
        sa.Column("filing_year", sa.Integer(), nullable=False),
        sa.Column("factor_text", sa.Text(), nullable=False),
        sa.Column("factor_hash", sa.String(), nullable=False),
        sa.Column("source_page", sa.Integer(), nullable=True),
        sa.Column("filing_date", sa.Date(), nullable=True),
        sa.UniqueConstraint("ticker", "accession_no", "factor_hash", name="uq_risk_factors_ticker_accession_hash"),
    )
    op.create_index("ix_risk_factors_ticker", "risk_factors", ["ticker"], unique=False)
    op.create_index("ix_risk_factors_accession_no", "risk_factors", ["accession_no"], unique=False)

    op.create_table(
        "risk_deltas",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("ticker", sa.String(), sa.ForeignKey("tickers.symbol", ondelete="CASCADE"), nullable=False),
        sa.Column("filing_year", sa.Integer(), nullable=False),
        sa.Column("delta_type", sa.String(), nullable=False),
        sa.Column("factor_text", sa.Text(), nullable=False),
        sa.Column("prior_text", sa.Text(), nullable=True),
        sa.Column("accession_no", sa.String(), nullable=False),
        sa.Column("prior_accession_no", sa.String(), nullable=True),
        sa.Column("source_page", sa.Integer(), nullable=True),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("ticker", "filing_year", "delta_type", "accession_no", "factor_text", name="uq_risk_deltas_dedup"),
    )
    op.create_index("ix_risk_deltas_ticker", "risk_deltas", ["ticker"], unique=False)
    op.create_index("ix_risk_deltas_accession_no", "risk_deltas", ["accession_no"], unique=False)

    op.create_table(
        "insider_trades",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("ticker", sa.String(), sa.ForeignKey("tickers.symbol", ondelete="CASCADE"), nullable=False),
        sa.Column("insider_name", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("transaction_type", sa.String(), nullable=False),
        sa.Column("shares", sa.Numeric(20, 4), nullable=True),
        sa.Column("price_per_share", sa.Numeric(20, 4), nullable=True),
        sa.Column("total_value", sa.Numeric(20, 4), nullable=True),
        sa.Column("is_10b5_1", sa.Boolean(), nullable=False),
        sa.Column("transaction_date", sa.Date(), nullable=True),
        sa.Column("accession_no", sa.String(), nullable=False),
        sa.Column("source_page", sa.Integer(), nullable=True),
        sa.Column("filing_date", sa.Date(), nullable=True),
        sa.UniqueConstraint("ticker", "accession_no", "insider_name", "transaction_date", "transaction_type", "shares", "price_per_share", name="uq_insider_trades_dedup"),
    )
    op.create_index("ix_insider_trades_ticker", "insider_trades", ["ticker"], unique=False)
    op.create_index("ix_insider_trades_accession_no", "insider_trades", ["accession_no"], unique=False)

    op.create_table(
        "superinvestor_holdings",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("investor_name", sa.Text(), nullable=False),
        sa.Column("fund_name", sa.Text(), nullable=False),
        sa.Column("fund_cik", sa.String(), nullable=False),
        sa.Column("ticker", sa.String(), sa.ForeignKey("tickers.symbol", ondelete="CASCADE"), nullable=False),
        sa.Column("period", sa.String(), nullable=False),
        sa.Column("shares_held", sa.Numeric(20, 4), nullable=True),
        sa.Column("market_value", sa.Numeric(20, 4), nullable=True),
        sa.Column("qoq_change", sa.String(), nullable=True),
        sa.Column("qoq_change_pct", sa.Numeric(10, 4), nullable=True),
        sa.Column("accession_no", sa.String(), nullable=False),
        sa.Column("source_page", sa.Integer(), nullable=True),
        sa.Column("filing_date", sa.Date(), nullable=True),
        sa.UniqueConstraint("investor_name", "ticker", "period", "accession_no", name="uq_superinvestor_holdings_dedup"),
    )
    op.create_index("ix_superinvestor_holdings_fund_cik", "superinvestor_holdings", ["fund_cik"], unique=False)
    op.create_index("ix_superinvestor_holdings_ticker", "superinvestor_holdings", ["ticker"], unique=False)
    op.create_index("ix_superinvestor_holdings_accession_no", "superinvestor_holdings", ["accession_no"], unique=False)

    op.create_table(
        "special_situations",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("ticker", sa.String(), sa.ForeignKey("tickers.symbol", ondelete="SET NULL"), nullable=True),
        sa.Column("situation_type", sa.Text(), nullable=False),
        sa.Column("filing_type", sa.String(), nullable=False),
        sa.Column("color", sa.String(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("accession_no", sa.String(), nullable=False),
        sa.Column("cik", sa.String(), nullable=False),
        sa.Column("source_page", sa.Integer(), nullable=True),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("filing_date", sa.Date(), nullable=True),
        sa.UniqueConstraint("accession_no", "ticker", "situation_type", name="uq_special_situations_accession_ticker_type"),
    )
    op.create_index("ix_special_situations_ticker", "special_situations", ["ticker"], unique=False)

    op.create_table(
        "notes",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("ticker", sa.String(), sa.ForeignKey("tickers.symbol", ondelete="CASCADE"), nullable=False),
        sa.Column("note_text", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "ticker", name="uq_notes_user_ticker"),
    )
    op.create_index("ix_notes_user_id", "notes", ["user_id"], unique=False)
    op.create_index("ix_notes_ticker", "notes", ["ticker"], unique=False)

    op.create_table(
        "highlights",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("accession_no", sa.String(), nullable=False),
        sa.Column("page", sa.Integer(), nullable=False),
        sa.Column("coords", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("color", sa.String(), nullable=True),
        sa.Column("note_text", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_highlights_user_id", "highlights", ["user_id"], unique=False)
    op.create_index("ix_highlights_accession_no", "highlights", ["accession_no"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_highlights_accession_no", table_name="highlights")
    op.drop_index("ix_highlights_user_id", table_name="highlights")
    op.drop_table("highlights")
    op.drop_index("ix_notes_ticker", table_name="notes")
    op.drop_index("ix_notes_user_id", table_name="notes")
    op.drop_table("notes")
    op.drop_index("ix_special_situations_ticker", table_name="special_situations")
    op.drop_table("special_situations")
    op.drop_index("ix_superinvestor_holdings_accession_no", table_name="superinvestor_holdings")
    op.drop_index("ix_superinvestor_holdings_ticker", table_name="superinvestor_holdings")
    op.drop_index("ix_superinvestor_holdings_fund_cik", table_name="superinvestor_holdings")
    op.drop_table("superinvestor_holdings")
    op.drop_index("ix_insider_trades_accession_no", table_name="insider_trades")
    op.drop_index("ix_insider_trades_ticker", table_name="insider_trades")
    op.drop_table("insider_trades")
    op.drop_index("ix_risk_deltas_accession_no", table_name="risk_deltas")
    op.drop_index("ix_risk_deltas_ticker", table_name="risk_deltas")
    op.drop_table("risk_deltas")
    op.drop_index("ix_risk_factors_accession_no", table_name="risk_factors")
    op.drop_index("ix_risk_factors_ticker", table_name="risk_factors")
    op.drop_table("risk_factors")
    op.drop_index("ix_debt_schedule_accession_no", table_name="debt_schedule")
    op.drop_index("ix_debt_schedule_ticker", table_name="debt_schedule")
    op.drop_table("debt_schedule")
    op.drop_index("ix_segments_accession_no", table_name="segments")
    op.drop_index("ix_segments_ticker", table_name="segments")
    op.drop_table("segments")
    op.drop_index("ix_financials_accession_no", table_name="financials")
    op.drop_index("ix_financials_ticker", table_name="financials")
    op.drop_table("financials")
    op.drop_table("users")
    op.drop_index("ix_tickers_cik", table_name="tickers")
    op.drop_table("tickers")
    op.drop_index("ix_feed_events_cik", table_name="feed_events")
    op.drop_index("ix_feed_events_ticker", table_name="feed_events")
    op.drop_table("feed_events")
