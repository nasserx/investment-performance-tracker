"""Transaction repository for database operations on Transaction model."""

from typing import List
from portfolio_app.repositories.base import BaseRepository
from portfolio_app.models.transaction import Transaction


class TransactionRepository(BaseRepository[Transaction]):
    """Repository for Transaction model database operations."""

    def get_by_fund_id(self, fund_id: int) -> List[Transaction]:
        """Get all transactions for a specific fund.

        Args:
            fund_id: The fund ID

        Returns:
            List of transactions for the fund
        """
        return self.model.query.filter_by(fund_id=fund_id).all()

    def get_by_symbol(self, fund_id: int, symbol: str) -> List[Transaction]:
        """Get all transactions for a specific symbol in a fund.

        Args:
            fund_id: The fund ID
            symbol: The symbol

        Returns:
            List of transactions for the symbol
        """
        return self.model.query.filter_by(
            fund_id=fund_id,
            symbol=symbol.strip().upper()
        ).order_by(Transaction.date.asc()).all()
