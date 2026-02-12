"""Transaction model for buy/sell operations."""

from datetime import datetime
from decimal import Decimal
from sqlalchemy import Numeric, CheckConstraint
from portfolio_app import db


class Transaction(db.Model):
    """Transaction model for buy/sell operations"""
    __tablename__ = 'transaction'

    id = db.Column(db.Integer, primary_key=True)
    fund_id = db.Column('capital_id', db.Integer, db.ForeignKey('capital.id'), nullable=False)
    transaction_type = db.Column(db.String(10), nullable=False)  # Buy or Sell
    symbol = db.Column(db.String(20), nullable=True)
    # NOTE: Use higher precision to support crypto-style pricing (e.g. 0.0002344)
    price = db.Column(Numeric(20, 10), nullable=False)
    quantity = db.Column(Numeric(20, 10), nullable=False)
    fees = db.Column(Numeric(15, 2), nullable=False, default=0)
    total_cost = db.Column(Numeric(15, 2), nullable=False, default=0)
    average_cost = db.Column(Numeric(20, 10), nullable=False, default=0)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    notes = db.Column(db.Text, nullable=True)

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

    # Constraints
    __table_args__ = (
        CheckConstraint('price > 0', name='check_price_positive'),
        CheckConstraint('quantity > 0', name='check_quantity_positive'),
        CheckConstraint('fees >= 0', name='check_fees_non_negative'),
        CheckConstraint('total_cost >= 0', name='check_total_cost_non_negative'),
    )

    def calculate_total_cost(self):
        """Calculate and update total_cost based on transaction type.

        This is a simple calculation method that updates the total_cost column
        from existing model data (price, quantity, fees).
        """
        price = Decimal(str(self.price))
        quantity = Decimal(str(self.quantity))
        fees = Decimal(str(self.fees))
        gross = price * quantity

        if self.transaction_type == 'Sell':
            self.total_cost = gross - fees
        else:  # Buy
            self.total_cost = gross + fees

    def to_dict(self):
        """Convert model to dictionary"""
        return {
            'id': self.id,
            'fund_id': self.fund_id,
            'category': self.fund.category,
            'transaction_type': self.transaction_type,
            'symbol': (self.symbol or '').upper(),
            'price': float(self.price),
            'quantity': float(self.quantity),
            'fees': float(self.fees),
            'total_cost': float(self.total_cost),
            'average_cost': float(self.average_cost),
            'date': self.date.strftime('%Y-%m-%d %H:%M'),
            'date_short': self.date.strftime('%b %d, %Y'),
            'date_full': self.date.strftime('%B %d, %Y at %H:%M'),
            'notes': self.notes or ''
        }
