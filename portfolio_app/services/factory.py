"""Service factory — single source of truth for service instantiation."""

import logging
from flask import g
from portfolio_app import db
from portfolio_app.models import Fund, FundEvent, Transaction, Asset
from portfolio_app.repositories import (
    FundRepository,
    FundEventRepository,
    TransactionRepository,
    AssetRepository,
)
from portfolio_app.services.fund_service import FundService
from portfolio_app.services.transaction_service import TransactionService
from portfolio_app.services.portfolio_service import PortfolioService

logger = logging.getLogger(__name__)


class Services:
    """Container holding all service and repository instances for a request."""

    __slots__ = (
        'fund_repo', 'event_repo', 'transaction_repo', 'asset_repo',
        'fund_service', 'transaction_service', 'portfolio_service',
    )

    def __init__(self):
        self.fund_repo = FundRepository(Fund, db)
        self.event_repo = FundEventRepository(FundEvent, db)
        self.transaction_repo = TransactionRepository(Transaction, db)
        self.asset_repo = AssetRepository(Asset, db)

        self.fund_service = FundService(self.fund_repo, self.event_repo)
        self.transaction_service = TransactionService(
            self.transaction_repo, self.asset_repo, self.fund_repo,
        )
        self.portfolio_service = PortfolioService(self.fund_repo)


def get_services() -> Services:
    """Get service instances, cached per request in Flask's ``g`` object."""
    if not hasattr(g, '_services'):
        g._services = Services()
    return g._services
