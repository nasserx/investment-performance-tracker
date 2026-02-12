"""FundEvent repository for database operations on FundEvent model."""

from typing import List
from portfolio_app.repositories.base import BaseRepository
from portfolio_app.models.fund_event import FundEvent


class FundEventRepository(BaseRepository[FundEvent]):
    """Repository for FundEvent model database operations."""

    def get_by_fund_id(self, fund_id: int) -> List[FundEvent]:
        """Get all events for a specific fund.

        Args:
            fund_id: The fund ID

        Returns:
            List of events for the fund ordered by date
        """
        return self.model.query.filter_by(
            fund_id=fund_id
        ).order_by(FundEvent.date.asc()).all()
