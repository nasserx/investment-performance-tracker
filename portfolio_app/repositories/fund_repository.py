"""Fund repository for database operations on Fund model."""

from typing import Optional, List
from portfolio_app.repositories.base import BaseRepository
from portfolio_app.models.fund import Fund


class FundRepository(BaseRepository[Fund]):
    """Repository for Fund model database operations."""

    def get_by_category(self, category: str) -> Optional[Fund]:
        """Get fund by category name.

        Args:
            category: The category name

        Returns:
            The fund if found, None otherwise
        """
        return self.model.query.filter_by(category=category).first()

    def get_available_categories(self, all_categories: List[str]) -> List[str]:
        """Get list of categories that don't have funds yet.

        Args:
            all_categories: List of all possible categories

        Returns:
            List of available (unused) categories
        """
        existing = [f.category for f in self.get_all()]
        return [cat for cat in all_categories if cat not in existing]
