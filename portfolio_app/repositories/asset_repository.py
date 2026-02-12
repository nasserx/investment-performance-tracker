"""Asset repository for database operations on Asset model."""

from typing import Optional, List
from portfolio_app.repositories.base import BaseRepository
from portfolio_app.models.asset import Asset


class AssetRepository(BaseRepository[Asset]):
    """Repository for Asset model database operations."""

    def get_by_fund_and_symbol(self, fund_id: int, symbol: str) -> Optional[Asset]:
        """Get asset by fund ID and symbol.

        Args:
            fund_id: The fund ID
            symbol: The asset symbol

        Returns:
            The asset if found, None otherwise
        """
        return self.model.query.filter_by(
            fund_id=fund_id,
            symbol=symbol.strip().upper()
        ).first()

    def get_by_fund_id(self, fund_id: int) -> List[Asset]:
        """Get all assets for a specific fund.

        Args:
            fund_id: The fund ID

        Returns:
            List of assets for the fund
        """
        return self.model.query.filter_by(fund_id=fund_id).all()
