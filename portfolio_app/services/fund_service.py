"""Fund service for fund-related business logic."""

from decimal import Decimal
from typing import Optional, Any
from portfolio_app.models.fund import Fund
from portfolio_app.models.fund_event import FundEvent
from portfolio_app.repositories.fund_repository import FundRepository
from portfolio_app.repositories.fund_event_repository import FundEventRepository
from portfolio_app.utils.constants import EventType


class FundService:
    """Service for fund-related business logic."""

    def __init__(self, fund_repo: FundRepository, event_repo: FundEventRepository):
        """Initialize service with repositories.

        Args:
            fund_repo: Fund repository
            event_repo: FundEvent repository
        """
        self.fund_repo = fund_repo
        self.event_repo = event_repo

    def create_fund(self, category: str, amount: Decimal, notes: str = 'Initial funding') -> Fund:
        """Create new fund with initial event.

        Args:
            category: Fund category name
            amount: Initial amount
            notes: Optional notes for the initial event

        Returns:
            The created fund

        Raises:
            ValueError: If fund with this category already exists
        """
        # Validate
        if self.fund_repo.get_by_category(category):
            raise ValueError('Fund already exists')

        # Create fund
        fund = Fund(category=category, amount=amount)
        self.fund_repo.add(fund)
        self.fund_repo.flush()  # Get fund.id

        # Create initial event
        event = FundEvent(
            fund_id=fund.id,
            event_type=EventType.INITIAL,
            amount_delta=amount,
            notes=notes
        )
        self.event_repo.add(event)
        self.fund_repo.commit()

        return fund

    def deposit_funds(self, fund_id: int, amount_delta: Decimal, notes: Optional[str] = None) -> Fund:
        """Deposit funds to category.

        Args:
            fund_id: Fund ID
            amount_delta: Amount to deposit
            notes: Optional notes

        Returns:
            Updated fund

        Raises:
            ValueError: If fund not found
        """
        fund = self.fund_repo.get_by_id(fund_id)
        if not fund:
            raise ValueError('Fund not found')

        fund.amount = Decimal(str(fund.amount)) + amount_delta

        event = FundEvent(
            fund_id=fund_id,
            event_type=EventType.DEPOSIT,
            amount_delta=amount_delta,
            notes=notes
        )
        self.event_repo.add(event)
        self.fund_repo.commit()

        return fund

    def withdraw_funds(self, fund_id: int, amount_delta: Decimal, notes: Optional[str] = None) -> Fund:
        """Withdraw funds from category.

        Args:
            fund_id: Fund ID
            amount_delta: Amount to withdraw (positive number)
            notes: Optional notes

        Returns:
            Updated fund

        Raises:
            ValueError: If fund not found
        """
        fund = self.fund_repo.get_by_id(fund_id)
        if not fund:
            raise ValueError('Fund not found')

        fund.amount = Decimal(str(fund.amount)) - amount_delta

        event = FundEvent(
            fund_id=fund_id,
            event_type=EventType.WITHDRAWAL,
            amount_delta=-amount_delta,
            notes=notes
        )
        self.event_repo.add(event)
        self.fund_repo.commit()

        return fund

    def delete_fund(self, fund_id: int) -> str:
        """Delete fund (cascade deletes events and transactions).

        Args:
            fund_id: Fund ID

        Returns:
            Category name of deleted fund

        Raises:
            ValueError: If fund not found
        """
        fund = self.fund_repo.get_by_id(fund_id)
        if not fund:
            raise ValueError('Fund not found')

        category = fund.category
        self.fund_repo.delete(fund)
        self.fund_repo.commit()

        return category

    def update_fund_event(self, event_id: int, amount_delta: Decimal, notes: Optional[str] = None, date: Optional[Any] = None) -> FundEvent:
        """Update a fund event.

        Args:
            event_id: Event ID
            amount_delta: New amount delta
            notes: New notes
            date: New date

        Returns:
            Updated event

        Raises:
            ValueError: If event not found
        """
        event = self.event_repo.get_by_id(event_id)
        if not event:
            raise ValueError('Event not found')

        # Calculate the difference to apply to fund
        old_delta = Decimal(str(event.amount_delta))
        new_delta = amount_delta
        delta_change = new_delta - old_delta

        # Update fund amount
        fund = self.fund_repo.get_by_id(event.fund_id)
        if fund:
            fund.amount = Decimal(str(fund.amount)) + delta_change

        # Update event
        event.amount_delta = amount_delta
        if notes is not None:
            event.notes = notes
        if date is not None:
            event.date = date

        self.fund_repo.commit()
        return event

    def delete_fund_event(self, event_id: int) -> int:
        """Delete a fund event.

        Args:
            event_id: Event ID

        Returns:
            Fund ID of the deleted event

        Raises:
            ValueError: If event not found or it's an initial event
        """
        event = self.event_repo.get_by_id(event_id)
        if not event:
            raise ValueError('Event not found')

        if event.event_type == EventType.INITIAL:
            raise ValueError('Cannot delete initial event')

        # Reverse the amount from fund
        fund = self.fund_repo.get_by_id(event.fund_id)
        if fund:
            fund.amount = Decimal(str(fund.amount)) - Decimal(str(event.amount_delta))

        fund_id = event.fund_id
        self.event_repo.delete(event)
        self.fund_repo.commit()

        return fund_id
