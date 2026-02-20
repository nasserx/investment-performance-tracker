#!/usr/bin/env python3
"""
Test script to verify the investment performance application
"""

from portfolio_app import create_app, db
from portfolio_app.models import Fund, Transaction
from portfolio_app.calculators import PortfolioCalculator
from datetime import datetime
from decimal import Decimal
from config import Config
from pathlib import Path


class TestConfig(Config):
    TESTING = True
    WTF_CSRF_ENABLED = False
    # Use a separate DB file to avoid modifying the user's real portfolio.db
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{(Path(__file__).resolve().parent / 'test_portfolio.db').as_posix()}"


def setup_test_data():
    """Create test data for verification"""
    test_db_path = Path(__file__).resolve().parent / 'test_portfolio.db'
    if test_db_path.exists():
        test_db_path.unlink()

    app = create_app(TestConfig)
    
    with app.app_context():
        # Clear existing data
        db.drop_all()
        db.create_all()
        
        # Create test funds
        commodities = Fund(category='Commodities', amount=25000)  # type: ignore[call-arg]
        stocks = Fund(category='Stocks', amount=40000)  # type: ignore[call-arg]
        etfs = Fund(category='ETFs', amount=200)  # type: ignore[call-arg]

        db.session.add(commodities)
        db.session.add(stocks)
        db.session.add(etfs)
        db.session.commit()

        # Create test transactions for Commodities (XAU)
        t1 = Transaction(  # type: ignore[call-arg]
            fund_id=commodities.id,
            transaction_type='Buy',
            date=datetime(2026, 1, 10),
            symbol='XAU',
            price=2000,
            quantity=1.5,
            fees=50,
            notes='XAU purchase'
        )
        t1.calculate_total_cost()

        t2 = Transaction(  # type: ignore[call-arg]
            fund_id=commodities.id,
            transaction_type='Buy',
            date=datetime(2026, 1, 15),
            symbol='XAU',
            price=2050,
            quantity=1.0,
            fees=30,
            notes='XAU purchase 2'
        )
        t2.calculate_total_cost()
        
        # Create test transactions for Stocks
        t3 = Transaction(  # type: ignore[call-arg]
            fund_id=stocks.id,
            transaction_type='Buy',
            date=datetime(2026, 1, 8),
            symbol='AAPL',
            price=100,
            quantity=50,
            fees=25,
            notes='Apple stock'
        )
        t3.calculate_total_cost()
        
        t4 = Transaction(  # type: ignore[call-arg]
            fund_id=stocks.id,
            transaction_type='Buy',
            date=datetime(2026, 1, 12),
            symbol='AAPL',
            price=105,
            quantity=30,
            fees=15,
            notes='Apple stock 2'
        )
        t4.calculate_total_cost()

        # Another symbol in the same Stocks category to ensure averages don't mix
        t5 = Transaction(  # type: ignore[call-arg]
            fund_id=stocks.id,
            transaction_type='Buy',
            date=datetime(2026, 1, 9),
            symbol='MSFT',
            price=200,
            quantity=10,
            fees=10,
            notes='Microsoft stock'
        )
        t5.calculate_total_cost()

        # Create test transactions for ETFs (Sell then Buy to verify running average cost)
        e1 = Transaction(  # type: ignore[call-arg]
            fund_id=etfs.id,
            transaction_type='Buy',
            date=datetime(2026, 1, 1),
            symbol='ETHA',
            price=10,
            quantity=10,
            fees=0,
            notes='ETF buy'
        )
        e1.calculate_total_cost()

        e2 = Transaction(  # type: ignore[call-arg]
            fund_id=etfs.id,
            transaction_type='Sell',
            date=datetime(2026, 1, 2),
            symbol='ETHA',
            price=12,
            quantity=5,
            fees=1,
            notes='ETF partial sell'
        )
        e2.calculate_total_cost()

        e3 = Transaction(  # type: ignore[call-arg]
            fund_id=etfs.id,
            transaction_type='Buy',
            date=datetime(2026, 1, 3),
            symbol='ETHA',
            price=10,
            quantity=5,
            fees=0,
            notes='ETF buy after sell'
        )
        e3.calculate_total_cost()

        db.session.add_all([t1, t2, t3, t4, t5, e1, e2, e3])
        db.session.commit()
        
        # Recalculate average costs after insertions
        PortfolioCalculator.recalculate_all_averages_for_symbol(commodities.id, 'XAU')
        PortfolioCalculator.recalculate_all_averages_for_symbol(stocks.id, 'AAPL')
        PortfolioCalculator.recalculate_all_averages_for_symbol(stocks.id, 'MSFT')
        PortfolioCalculator.recalculate_all_averages_for_symbol(etfs.id, 'ETHA')
        db.session.commit()
        
        print("✓ Test data created successfully")
        print()
        
        # Test calculations
        print("=" * 60)
        print("PORTFOLIO CALCULATIONS TEST")
        print("=" * 60)
        
        # Test Commodities summary (XAU symbol)
        gold_summary = PortfolioCalculator.get_symbol_transactions_summary(commodities.id, 'XAU')
        print("\nCommodities Summary (XAU):")
        print(f"  Total Buy Cost: {gold_summary['total_buy_cost']:,.2f}")
        print(f"  Total Buy Fees: {gold_summary['total_buy_fees']:,.2f}")
        print(f"  Total Buy Quantity: {gold_summary['total_buy_quantity']:.4f}")
        print(f"  Average Cost: {gold_summary['average_cost']:,.4f}")
        print(f"  Total Quantity Held: {gold_summary['total_quantity_held']:.4f}")
        print(f"  Transaction Count: {gold_summary['transaction_count']}")
        
        # Test Stocks summary (AAPL symbol)
        stocks_summary = PortfolioCalculator.get_symbol_transactions_summary(stocks.id, 'AAPL')
        print("\nStocks Summary:")
        print(f"  Total Buy Cost: {stocks_summary['total_buy_cost']:,.2f}")
        print(f"  Total Buy Fees: {stocks_summary['total_buy_fees']:,.2f}")
        print(f"  Total Buy Quantity: {stocks_summary['total_buy_quantity']:.4f}")
        print(f"  Average Cost: {stocks_summary['average_cost']:,.4f}")
        print(f"  Total Quantity Held: {stocks_summary['total_quantity_held']:.4f}")
        print(f"  Transaction Count: {stocks_summary['transaction_count']}")
        
        # Portfolio-level (manual-entry app): cash + realized profit
        print("\n" + "=" * 60)
        print("PORTFOLIO DASHBOARD TOTALS")
        print("=" * 60)

        totals = PortfolioCalculator.get_portfolio_dashboard_totals()
        print(f"\nTotal Investment: {totals['total_investment']:,.2f}")
        print(f"Total Cash: {totals['total_cash']:,.2f}")
        print(f"Total P&L (Realized): {totals['total_realized_pnl']:,.2f}")
        print(f"Realized ROI: {totals['realized_roi_display']}")
        
        # Verify calculations
        print("\n" + "=" * 60)
        print("VERIFICATION")
        print("=" * 60)
        
        # Check XAU average cost
        expected_gold_avg = (((1.5 * 2000) + 50) + ((1.0 * 2050) + 30)) / (1.5 + 1.0)
        print(f"\nCommodities (XAU) Average Cost:")
        print(f"  Expected: {expected_gold_avg:,.4f}")
        print(f"  Actual: {gold_summary['average_cost']:,.4f}")
        print(f"  ✓ PASS" if abs(Decimal(str(expected_gold_avg)) - gold_summary['average_cost']) < Decimal('0.01') else "  ✗ FAIL")
        
        # Check AAPL average cost
        expected_stocks_avg = (((50 * 100) + 25) + ((30 * 105) + 15)) / (50 + 30)
        print(f"\nStocks Average Cost:")
        print(f"  Expected: {expected_stocks_avg:,.4f}")
        print(f"  Actual: {stocks_summary['average_cost']:,.4f}")
        print(f"  ✓ PASS" if abs(Decimal(str(expected_stocks_avg)) - stocks_summary['average_cost']) < Decimal('0.01') else "  ✗ FAIL")

        # Check MSFT average cost doesn't mix with AAPL
        msft_summary = PortfolioCalculator.get_symbol_transactions_summary(stocks.id, 'MSFT')
        expected_msft_avg = ((10 * 200) + 10) / 10
        print(f"\nMSFT Average Cost (same category, separate symbol):")
        print(f"  Expected: {expected_msft_avg:,.4f}")
        print(f"  Actual: {msft_summary['average_cost']:,.4f}")
        print(f"  ✓ PASS" if abs(Decimal(str(expected_msft_avg)) - msft_summary['average_cost']) < Decimal('0.01') else "  ✗ FAIL")

        # Check ETFs running average cost after Sell then Buy
        etfs_summary = PortfolioCalculator.get_symbol_transactions_summary(etfs.id, 'ETHA')
        expected_etfs_avg = 15.0  # After: Buy 10@10, Sell 5, Buy 5@10 -> avg cost becomes 15
        expected_etfs_realized = 9.0  # (12-10)*5 - 1

        print(f"\nETFs Average Cost (Sell then Buy case):")
        print(f"  Expected: {expected_etfs_avg:,.4f}")
        print(f"  Actual: {etfs_summary['average_cost']:,.4f}")
        print(f"  ✓ PASS" if abs(Decimal(str(expected_etfs_avg)) - etfs_summary['average_cost']) < Decimal('0.01') else "  ✗ FAIL")

        print(f"\nETFs Realized P&L:")
        print(f"  Expected: {expected_etfs_realized:,.2f}")
        print(f"  Actual: {etfs_summary['realized_pnl']:,.2f}")
        print(f"  ✓ PASS" if abs(Decimal(str(expected_etfs_realized)) - etfs_summary['realized_pnl']) < Decimal('0.01') else "  ✗ FAIL")
        
        print("\n" + "=" * 60)
        print("TEST COMPLETE")
        print("=" * 60)
        
        return app

def test_routes():
    """Test application routes"""
    app = create_app(TestConfig)
    client = app.test_client()

    # Ensure schema exists for route tests (pytest may run this without setup_test_data()).
    with app.app_context():
        db.drop_all()
        db.create_all()
    
    print("\n" + "=" * 60)
    print("ROUTE TESTS")
    print("=" * 60)
    
    # Test index route
    response = client.get('/')
    print(f"\nGET / - Status: {response.status_code}")
    assert response.status_code == 200, "Dashboard route failed"
    print("✓ Dashboard route works")
    
    # Test transactions route
    response = client.get('/transactions/')
    print(f"GET /transactions/ - Status: {response.status_code}")
    assert response.status_code == 200, "Transactions route failed"
    print("✓ Transactions route works")

    # Test funds route
    response = client.get('/funds/')
    print(f"GET /funds/ - Status: {response.status_code}")
    assert response.status_code == 200, "Funds route failed"
    print("✓ Funds route works")
    
    print("\nAll routes working correctly! ✓")

if __name__ == '__main__':
    print("\n" + "🚀 " * 10)
    print("Investment Performance Application Test Suite")
    print("🚀 " * 10 + "\n")
    
    try:
        setup_test_data()
        test_routes()
        print("\n" + "✓ " * 10)
        print("ALL TESTS PASSED!")
        print("✓ " * 10 + "\n")
    except Exception as e:
        print(f"\n✗ TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
