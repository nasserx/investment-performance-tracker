"""FundEvent model for funding events (deposits/withdrawals)."""

from datetime import datetime
from sqlalchemy import Numeric, Index
from portfolio_app import db


class FundEvent(db.Model):
    """Funding events (deposits/withdrawals) per category."""

    __tablename__ = 'capital_event'

    id = db.Column(db.Integer, primary_key=True)
    fund_id = db.Column('capital_id', db.Integer, db.ForeignKey('capital.id'), nullable=False)

    # Initial / Deposit / Withdrawal
    event_type = db.Column(db.String(20), nullable=False)

    # Store signed delta (deposit positive, withdrawal negative)
    amount_delta = db.Column('amount_usd_delta', Numeric(15, 2), nullable=False, default=0)

    date = db.Column(db.DateTime, default=datetime.utcnow)
    notes = db.Column(db.Text, nullable=True)

    __table_args__ = (
        Index('ix_fund_event_fund_date', fund_id, date),
    )

    @property
    def date_short(self):
        if not self.date:
            return ''
        return self.date.strftime('%Y-%m-%d')

    @property
    def date_full(self):
        if not self.date:
            return ''
        return self.date.strftime('%Y-%m-%d %H:%M')
