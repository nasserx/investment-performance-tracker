"""Portfolio calculator for financial calculations."""

from decimal import Decimal
from sqlalchemy import case, func
from portfolio_app.models import Fund, Transaction

ZERO = Decimal('0')


def _safe_divide(numerator, denominator, default=ZERO):
    """Divide numerator by denominator, returning default if denominator is zero."""
    return numerator / denominator if denominator else default


class PortfolioCalculator:
    """Utility class for portfolio calculations"""

    @staticmethod
    def _to_decimal(value) -> Decimal:
        return Decimal(str(value))

    @staticmethod
    def normalize_symbol(symbol) -> str:
        if symbol is None:
            return ''
        return str(symbol).strip().upper()

    @staticmethod
    def get_quantity_held_for_fund(fund_id, exclude_transaction_id=None):
        """Return current quantity held for a fund.

        This is used for validation (e.g., prevent selling more than held).
        """
        query = Transaction.query.filter_by(fund_id=fund_id)
        if exclude_transaction_id is not None:
            query = query.filter(Transaction.id != exclude_transaction_id)
        transactions = query.order_by(Transaction.date.asc()).all()

        running_quantity = ZERO
        for t in transactions:
            qty = PortfolioCalculator._to_decimal(t.quantity)
            if t.transaction_type == 'Buy':
                running_quantity += qty
            elif t.transaction_type == 'Sell':
                running_quantity -= qty

        return running_quantity

    @staticmethod
    def get_quantity_held_for_symbol(fund_id, symbol, exclude_transaction_id=None):
        """Return current quantity held for a specific symbol inside a fund/category."""
        normalized = PortfolioCalculator.normalize_symbol(symbol)

        query = Transaction.query.filter_by(fund_id=fund_id, symbol=normalized)
        if exclude_transaction_id is not None:
            query = query.filter(Transaction.id != exclude_transaction_id)
        transactions = query.order_by(Transaction.date.asc()).all()

        running_quantity = ZERO
        for t in transactions:
            qty = PortfolioCalculator._to_decimal(t.quantity)
            if t.transaction_type == 'Buy':
                running_quantity += qty
            elif t.transaction_type == 'Sell':
                running_quantity -= qty

        return running_quantity

    @staticmethod
    def get_total_portfolio_value():
        """Total portfolio value (invested + cash across all categories)."""
        funds = Fund.query.all()
        total = ZERO
        for f in funds:
            cash = PortfolioCalculator.get_cash_balance_for_fund(f.id)
            tx_summary = PortfolioCalculator.get_category_transactions_summary(f.id)
            invested = Decimal(str(tx_summary['current_invested'] or 0))
            total += invested + cash
        return total

    @staticmethod
    def get_cash_balance_for_fund(fund_id, exclude_transaction_id=None) -> Decimal:
        """Compute current cash balance for a category from its funds + transactions.

        Funds table is a fixed reference (allocated funds). Cash balance is derived:
        cash = fund_amount - buy_outflows + sell_inflows.
        """
        fund = Fund.query.get(fund_id)
        if not fund:
            return ZERO

        cash = Decimal(str(fund.amount or 0))
        query = Transaction.query.filter_by(fund_id=fund_id)
        if exclude_transaction_id is not None:
            query = query.filter(Transaction.id != exclude_transaction_id)
        transactions = query.order_by(Transaction.date.asc()).all()

        for t in transactions:
            price = PortfolioCalculator._to_decimal(t.price)
            quantity = PortfolioCalculator._to_decimal(t.quantity)
            fees = PortfolioCalculator._to_decimal(t.fees)
            gross = price * quantity

            if t.transaction_type == 'Buy':
                cash -= gross + fees
            elif t.transaction_type == 'Sell':
                cash += gross - fees

        return cash

    @staticmethod
    def get_category_summary():
        """Get summary for each category.

        This app is manual-entry based (no live prices). Therefore, we treat
        funds as CASH balance per category and show only REALIZED profit.
        """
        funds = Fund.query.all()

        # First pass: compute per-category values
        categories = []
        portfolio_value = ZERO
        for fund in funds:
            fund_amount = Decimal(str(fund.amount or 0))

            realized_perf = PortfolioCalculator.get_realized_performance_for_fund(fund.id)
            realized_pnl = realized_perf['realized_pnl']

            transactions_summary = PortfolioCalculator.get_category_transactions_summary(fund.id)
            current_invested = Decimal(str(transactions_summary['current_invested'] or 0))

            cash = PortfolioCalculator.get_cash_balance_for_fund(fund.id)
            category_value = current_invested + cash
            portfolio_value += category_value

            total_value = fund_amount + realized_pnl

            realized_roi_percent = ZERO
            realized_roi_display = '—'
            if fund_amount > 0:
                realized_roi_percent = (realized_pnl / fund_amount) * 100
                realized_roi_display = f"{realized_roi_percent:+,.2f}%"

            categories.append({
                'fund': fund,
                'fund_amount': fund_amount,
                'realized_pnl': realized_pnl,
                'current_invested': current_invested,
                'cash': cash,
                'category_value': category_value,
                'total_value': total_value,
                'realized_roi_percent': realized_roi_percent,
                'realized_roi_display': realized_roi_display,
            })

        # Second pass: compute allocation based on portfolio value
        summary = []
        for cat in categories:
            allocation = (cat['category_value'] / portfolio_value * 100) if portfolio_value > 0 else ZERO

            summary.append({
                'category': cat['fund'].category,
                'amount': cat['fund_amount'],
                'allocation': Decimal(str(allocation)),
                'id': cat['fund'].id,
                'realized_pnl': cat['realized_pnl'],
                'current_invested': cat['current_invested'],
                'total_value': cat['total_value'],
                'cash': cat['cash'],
                'realized_roi_percent': cat['realized_roi_percent'],
                'realized_roi_display': cat['realized_roi_display'],
            })

        return summary, portfolio_value

    @staticmethod
    def get_realized_pnl_for_fund(fund_id):
        """Sum realized P&L across all symbols for a fund/category."""
        symbols = (
            Transaction.query.with_entities(Transaction.symbol)
            .filter_by(fund_id=fund_id)
            .distinct()
            .all()
        )
        realized = ZERO
        for (sym,) in symbols:
            sym_norm = PortfolioCalculator.normalize_symbol(sym)
            if not sym_norm:
                continue
            s = PortfolioCalculator.get_symbol_transactions_summary(fund_id, sym_norm)
            realized += Decimal(str(s['realized_pnl']))
        return realized

    @staticmethod
    def get_realized_performance_for_fund(fund_id):
        """Return realized P&L and its cost basis for a fund/category."""
        symbols = (
            Transaction.query.with_entities(Transaction.symbol)
            .filter_by(fund_id=fund_id)
            .distinct()
            .all()
        )

        realized_pnl = ZERO
        realized_cost_basis = ZERO
        realized_proceeds = ZERO

        for (sym,) in symbols:
            sym_norm = PortfolioCalculator.normalize_symbol(sym)
            if not sym_norm:
                continue
            s = PortfolioCalculator.get_symbol_transactions_summary(fund_id, sym_norm)
            realized_pnl += Decimal(str(s['realized_pnl']))
            realized_cost_basis += Decimal(str(s['realized_cost_basis']))
            realized_proceeds += Decimal(str(s['realized_proceeds']))

        return {
            'realized_pnl': realized_pnl,
            'realized_cost_basis': realized_cost_basis,
            'realized_proceeds': realized_proceeds,
        }

    @staticmethod
    def get_portfolio_dashboard_totals():
        """Dashboard totals.

        - Investment: fixed reference (Funds table)
        - Cash: derived from funds + transactions
        - ROI: realized ROI vs investment
        """
        funds = Fund.query.all()

        total_investment = ZERO
        total_cash = ZERO
        total_invested = ZERO
        total_realized_pnl = ZERO

        for fund in funds:
            total_investment += Decimal(str(fund.amount))

            cash = PortfolioCalculator.get_cash_balance_for_fund(fund.id)
            total_cash += cash

            tx_summary = PortfolioCalculator.get_category_transactions_summary(fund.id)
            total_invested += Decimal(str(tx_summary['current_invested'] or 0))

            realized_perf = PortfolioCalculator.get_realized_performance_for_fund(fund.id)
            total_realized_pnl += realized_perf['realized_pnl']

        total_value = total_invested + total_cash

        realized_roi_percent = ZERO
        realized_roi_display = '—'
        if total_investment > 0:
            realized_roi_percent = (total_realized_pnl / total_investment) * 100
            realized_roi_display = f"{realized_roi_percent:+,.2f}%"

        return {
            'total_investment': total_investment,
            'total_cash': total_cash,
            'total_realized_pnl': total_realized_pnl,
            'total_value': total_value,
            'realized_roi_percent': realized_roi_percent,
            'realized_roi_display': realized_roi_display,
        }

    @staticmethod
    def get_category_transactions_summary(fund_id):
        """Get aggregated transaction summary for a category"""
        # Aggregate across symbols without mixing average-cost calculations.
        symbols = (
            Transaction.query.with_entities(Transaction.symbol)
            .filter_by(fund_id=fund_id)
            .distinct()
            .all()
        )

        totals = {
            'total_buy_cost': ZERO,
            'total_buy_fees': ZERO,
            'total_buy_quantity': ZERO,
            'total_sell_cost': ZERO,
            'total_sell_fees': ZERO,
            'total_sell_quantity': ZERO,
            'total_quantity_held': ZERO,
            'realized_pnl': ZERO,
            'current_invested': ZERO,
            'transaction_count': 0,
        }

        for (sym,) in symbols:
            sym_norm = PortfolioCalculator.normalize_symbol(sym)
            if not sym_norm:
                continue
            summary = PortfolioCalculator.get_symbol_transactions_summary(fund_id, sym_norm)
            totals['total_buy_cost'] += Decimal(str(summary['total_buy_cost']))
            totals['total_buy_fees'] += Decimal(str(summary['total_buy_fees']))
            totals['total_buy_quantity'] += Decimal(str(summary['total_buy_quantity']))
            totals['total_sell_cost'] += Decimal(str(summary['total_sell_cost']))
            totals['total_sell_fees'] += Decimal(str(summary['total_sell_fees']))
            totals['total_sell_quantity'] += Decimal(str(summary['total_sell_quantity']))
            totals['total_quantity_held'] += Decimal(str(summary['total_quantity_held']))
            totals['realized_pnl'] += Decimal(str(summary['realized_pnl']))
            totals['current_invested'] += Decimal(str(summary['current_invested']))
            totals['transaction_count'] += int(summary['transaction_count'])

        # Average cost for category-level is not well-defined across multiple symbols.
        avg_cost = ZERO
        if totals['total_quantity_held'] > 0:
            # Approximate: weighted by current held qty using per-symbol avg cost.
            weighted_cost = ZERO
            for (sym,) in symbols:
                sym_norm = PortfolioCalculator.normalize_symbol(sym)
                if not sym_norm:
                    continue
                s = PortfolioCalculator.get_symbol_transactions_summary(fund_id, sym_norm)
                qty = Decimal(str(s['total_quantity_held']))
                weighted_cost += Decimal(str(s['average_cost'])) * qty
            avg_cost = weighted_cost / totals['total_quantity_held']

        return {
            'total_buy_cost': totals['total_buy_cost'],
            'total_buy_fees': totals['total_buy_fees'],
            'total_buy_quantity': totals['total_buy_quantity'],
            'total_sell_cost': totals['total_sell_cost'],
            'total_sell_fees': totals['total_sell_fees'],
            'total_sell_quantity': totals['total_sell_quantity'],
            'total_quantity_held': totals['total_quantity_held'],
            'average_cost': avg_cost,
            'transaction_count': totals['transaction_count'],
            'realized_pnl': totals['realized_pnl'],
            'current_invested': totals['current_invested'],
        }

    @staticmethod
    def get_symbol_transactions_summary(fund_id, symbol):
        """Get aggregated transaction summary for a specific symbol inside a category."""
        symbol = PortfolioCalculator.normalize_symbol(symbol)
        buy_first = case((Transaction.transaction_type == 'Buy', 0), else_=1)
        transactions = (
            Transaction.query.filter_by(fund_id=fund_id, symbol=symbol)
            .order_by(func.date(Transaction.date).asc(), buy_first, Transaction.id.asc())
            .all()
        )
        return PortfolioCalculator.get_symbol_transactions_summary_from_list(transactions)

    @staticmethod
    def get_symbol_transactions_summary_from_list(transactions):
        """Get aggregated summary from a list of transactions (ascending by date)."""
        total_buy_cost = ZERO
        total_buy_fees = ZERO
        total_buy_quantity = ZERO

        total_sell_cost = ZERO  # net proceeds (price*qty - fees)
        total_sell_fees = ZERO
        total_sell_quantity = ZERO

        realized_pnl = ZERO
        realized_cost_basis = ZERO
        realized_proceeds = ZERO
        running_quantity = ZERO
        running_cost = ZERO

        for t in transactions:
            price = PortfolioCalculator._to_decimal(t.price)
            quantity = PortfolioCalculator._to_decimal(t.quantity)
            fees = PortfolioCalculator._to_decimal(t.fees)

            if t.transaction_type == 'Buy':
                total_buy_cost += (price * quantity) + fees
                total_buy_fees += fees
                total_buy_quantity += quantity

                running_cost += (price * quantity) + fees
                running_quantity += quantity
            elif t.transaction_type == 'Sell':
                proceeds = (price * quantity) - fees
                total_sell_cost += proceeds
                total_sell_fees += fees
                total_sell_quantity += quantity

                realized_proceeds += proceeds

                avg_cost = _safe_divide(running_cost, running_quantity)
                realized_pnl += (price - avg_cost) * quantity - fees
                realized_cost_basis += avg_cost * quantity

                # Reduce position cost at average-cost basis
                running_quantity -= quantity
                running_cost -= avg_cost * quantity

        total_quantity_held = running_quantity
        avg_cost = _safe_divide(running_cost, running_quantity)

        return {
            'total_buy_cost': total_buy_cost,
            'total_buy_fees': total_buy_fees,
            'total_buy_quantity': total_buy_quantity,
            'total_sell_cost': total_sell_cost,
            'total_sell_fees': total_sell_fees,
            'total_sell_quantity': total_sell_quantity,
            'total_quantity_held': total_quantity_held,
            'average_cost': avg_cost,
            'transaction_count': len(transactions),
            'realized_pnl': realized_pnl,
            'realized_cost_basis': realized_cost_basis,
            'realized_proceeds': realized_proceeds,
            'current_invested': running_cost,
        }

    @staticmethod
    def recalculate_all_averages_for_fund(fund_id):
        """Recalculate average costs for all transactions of a fund.

        Note: internally recalculates per-symbol.
        """
        symbols = (
            Transaction.query.with_entities(Transaction.symbol)
            .filter_by(fund_id=fund_id)
            .distinct()
            .all()
        )

        updated = []
        for (sym,) in symbols:
            sym_norm = PortfolioCalculator.normalize_symbol(sym)
            if not sym_norm:
                continue
            updated.extend(PortfolioCalculator.recalculate_all_averages_for_symbol(fund_id, sym_norm))

        return updated

    @staticmethod
    def recalculate_all_averages_for_symbol(fund_id, symbol):
        """Recalculate average costs for all transactions of a (fund_id, symbol)."""
        symbol = PortfolioCalculator.normalize_symbol(symbol)
        buy_first = case((Transaction.transaction_type == 'Buy', 0), else_=1)
        transactions = (
            Transaction.query.filter_by(fund_id=fund_id, symbol=symbol)
            .order_by(func.date(Transaction.date).asc(), buy_first, Transaction.id.asc())
            .all()
        )

        running_quantity = ZERO
        running_cost = ZERO

        for transaction in transactions:
            # Ensure total_cost is consistent with transaction type (Buy vs Sell)
            transaction.calculate_total_cost()

            if transaction.transaction_type == 'Buy':
                transaction_cost = (Decimal(str(transaction.price)) * Decimal(str(transaction.quantity))) + Decimal(str(transaction.fees))
                running_cost += transaction_cost
                running_quantity += Decimal(str(transaction.quantity))

                if running_quantity > 0:
                    transaction.average_cost = running_cost / running_quantity
                else:
                    transaction.average_cost = 0

            elif transaction.transaction_type == 'Sell':
                sell_qty = Decimal(str(transaction.quantity))

                if running_quantity > 0:
                    transaction.average_cost = running_cost / running_quantity
                else:
                    transaction.average_cost = 0

                running_quantity -= sell_qty
                running_cost -= transaction.average_cost * sell_qty

        return transactions
