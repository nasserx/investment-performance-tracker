"""Transactions blueprint - Transaction and asset management routes."""

from flask import Blueprint, render_template, request, redirect, url_for, flash, g
from decimal import Decimal
import re
from sqlalchemy.exc import OperationalError
from portfolio_app import db
from portfolio_app.models import Fund, Transaction, Asset
from portfolio_app.services import TransactionService, ValidationError
from portfolio_app.repositories import TransactionRepository, AssetRepository, FundRepository
from portfolio_app.calculators import PortfolioCalculator
from portfolio_app.forms import TransactionAddForm, TransactionEditForm, AssetAddForm, AssetDeleteForm
from portfolio_app.utils import get_error_message, get_first_form_error, SuccessMessages, is_ajax_request, json_response
from config import Config

# Create blueprint
transactions_bp = Blueprint('transactions', __name__)


def get_services():
    """Get service instances (cached per request in g object)."""
    if not hasattr(g, 'transactions_services'):
        fund_repo = FundRepository(Fund, db)
        transaction_repo = TransactionRepository(Transaction, db)
        asset_repo = AssetRepository(Asset, db)
        transaction_service = TransactionService(transaction_repo, asset_repo, fund_repo)
        g.transactions_services = (transaction_service, fund_repo, transaction_repo, asset_repo)
    return g.transactions_services


def _get_transactions_page_context(category_filter=''):
    """Get context data for transactions page."""
    _, fund_repo, transaction_repo, asset_repo = get_services()
    category_filter = (category_filter or '').strip()
    funds = fund_repo.get_all()
    symbol_data = []

    def _decimal_places(value) -> int:
        if value is None:
            return 0
        d = Decimal(str(value))
        s = format(d, 'f')
        if '.' not in s:
            return 0
        fractional = s.split('.', 1)[1].rstrip('0')
        return len(fractional)

    for fund in funds:
        if category_filter and fund.category != category_filter:
            continue

        tracked_symbols = set()
        asset_by_symbol = {}

        try:
            fund_assets = asset_repo.get_by_fund_id(fund.id)
            for a in fund_assets:
                sym_norm = PortfolioCalculator.normalize_symbol(a.symbol)
                if sym_norm:
                    asset_by_symbol[sym_norm] = a
                    tracked_symbols.add(sym_norm)
        except OperationalError:
            asset_by_symbol = {}

        fund_transactions = transaction_repo.get_by_fund_id(fund.id)

        transactions_by_symbol = {}
        for t in fund_transactions:
            sym_norm = PortfolioCalculator.normalize_symbol(t.symbol)
            if not sym_norm:
                continue
            transactions_by_symbol.setdefault(sym_norm, []).append(t)
            tracked_symbols.add(sym_norm)

        for sym_norm in sorted(tracked_symbols):
            transactions = transactions_by_symbol.get(sym_norm, [])
            transactions_desc = list(reversed(transactions))

            price_decimals = max((_decimal_places(t.price) for t in transactions), default=0)
            price_decimals = max(0, min(int(price_decimals), 10))

            avg_cost_decimals = max(2, price_decimals)
            summary = PortfolioCalculator.get_symbol_transactions_summary_from_list(transactions)

            try:
                realized_pnl = Decimal(str(summary.get('realized_pnl', 0) or 0))
                realized_cost_basis = Decimal(str(summary.get('realized_cost_basis', 0) or 0))

                if realized_cost_basis > 0:
                    roi_percent = (realized_pnl / realized_cost_basis) * Decimal('100')
                    summary['roi_percent'] = float(roi_percent)
                    summary['roi_percent_display'] = f"{roi_percent:+,.2f}%"
                else:
                    summary['roi_percent'] = None
                    summary['roi_percent_display'] = '—'
            except Exception:
                summary['roi_percent'] = None
                summary['roi_percent_display'] = '—'

            group_id = re.sub(r'[^A-Za-z0-9_\-]+', '_', f"{fund.id}-{sym_norm}")
            asset = asset_by_symbol.get(sym_norm)
            symbol_data.append({
                'fund': fund,
                'symbol': sym_norm,
                'group_id': group_id,
                'transactions': transactions_desc,
                'summary': summary,
                'price_decimals': price_decimals,
                'avg_cost_decimals': avg_cost_decimals,
                'asset_id': asset.id if asset else None,
            })

    return {
        'symbol_data': symbol_data,
        'funds': funds,
        'transaction_types': Config.TRANSACTION_TYPES,
        'selected_category': category_filter,
    }


@transactions_bp.route('/')
def transaction_list():
    """Transactions page."""
    category_filter = request.args.get('category', '')
    ctx = _get_transactions_page_context(category_filter)
    return render_template(
        'transactions.html',
        **ctx,
        form_errors={},
        form_values={},
        open_modal=None,
    )


@transactions_bp.route('/add', methods=['POST'])
def transaction_add():
    """Add new transaction."""
    try:
        # Get services
        transaction_service, fund_repo, _, _ = get_services()

        # Get funds for validation
        funds = fund_repo.get_all()

        # Validate form
        form = TransactionAddForm(request.form, funds)
        if not form.validate():
            if is_ajax_request():
                return json_response(False, error=get_first_form_error(form.errors))

            ctx = _get_transactions_page_context()
            return render_template(
                'transactions.html',
                **ctx,
                form_errors={'transaction_add': form.errors},
                form_values={'transaction_add': request.form},
                open_modal='addTransactionModal',
            ), 400

        # Get cleaned data
        data = form.get_cleaned_data()

        # Add transaction using service
        transaction = transaction_service.add_transaction(
            fund_id=data['fund_id'],
            transaction_type=data['transaction_type'],
            symbol=data['symbol'],
            price=data['price'],
            quantity=data['quantity'],
            fees=data['fees'],
            notes=data['notes']
        )

        if is_ajax_request():
            return json_response(True, message=SuccessMessages.TRANSACTION_ADDED)

        flash(SuccessMessages.TRANSACTION_ADDED, 'success')
        return redirect(url_for('transactions.transaction_list'))

    except (ValueError, ValidationError) as e:
        if is_ajax_request():
            return json_response(False, error=get_error_message(e))
        flash(get_error_message(e), 'error')
        return redirect(url_for('transactions.transaction_list'))

    except Exception as e:
        db.session.rollback()
        if is_ajax_request():
            return json_response(False, error='Operation failed')
        flash('Operation failed', 'error')
        return redirect(url_for('transactions.transaction_list'))


@transactions_bp.route('/edit/<int:id>', methods=['POST'])
def transaction_edit(id):
    """Edit existing transaction."""
    try:
        # Get services
        transaction_service, _, transaction_repo, _ = get_services()

        # Get current transaction
        transaction = transaction_repo.get_by_id(id)
        if not transaction:
            if is_ajax_request():
                return json_response(False, error='Transaction not found')
            flash('Transaction not found', 'error')
            return redirect(url_for('transactions.transaction_list'))

        # Validate form
        form = TransactionEditForm(request.form, id, transaction.transaction_type)
        if not form.validate():
            if is_ajax_request():
                return json_response(False, error=get_first_form_error(form.errors))

            ctx = _get_transactions_page_context()
            return render_template(
                'transactions.html',
                **ctx,
                form_errors={'transaction_edit': form.errors},
                form_values={'transaction_edit': request.form},
                open_modal='editTransactionModal',
            ), 400

        # Get cleaned data
        data = form.get_cleaned_data()

        # Update transaction using service
        transaction_service.update_transaction(
            transaction_id=data['transaction_id'],
            price=data.get('price'),
            quantity=data.get('quantity'),
            fees=data.get('fees'),
            notes=data.get('notes'),
            symbol=data.get('symbol'),
            date=data.get('date')
        )

        if is_ajax_request():
            return json_response(True, message=SuccessMessages.TRANSACTION_UPDATED)

        flash(SuccessMessages.TRANSACTION_UPDATED, 'success')
        return redirect(url_for('transactions.transaction_list'))

    except (ValueError, ValidationError) as e:
        if is_ajax_request():
            return json_response(False, error=get_error_message(e))
        flash(get_error_message(e), 'error')
        return redirect(url_for('transactions.transaction_list'))

    except Exception as e:
        db.session.rollback()
        if is_ajax_request():
            return json_response(False, error='Operation failed')
        flash('Operation failed', 'error')
        return redirect(url_for('transactions.transaction_list'))


@transactions_bp.route('/delete/<int:id>', methods=['POST'])
def transaction_delete(id):
    """Delete transaction."""
    try:
        transaction_service, _, _, _ = get_services()
        transaction_service.delete_transaction(id)

        if is_ajax_request():
            return json_response(True, message=SuccessMessages.TRANSACTION_DELETED)
        flash(SuccessMessages.TRANSACTION_DELETED, 'success')

    except ValueError as e:
        if is_ajax_request():
            return json_response(False, error=get_error_message(e))
        flash(get_error_message(e), 'error')

    except Exception as e:
        db.session.rollback()
        if is_ajax_request():
            return json_response(False, error='Operation failed')
        flash('Operation failed', 'error')

    return redirect(url_for('transactions.transaction_list'))


@transactions_bp.route('/assets/add', methods=['POST'])
def asset_add():
    """Add tracked asset."""
    try:
        # Get services
        transaction_service, fund_repo, _, _ = get_services()

        # Get funds for validation
        funds = fund_repo.get_all()

        # Validate form
        form = AssetAddForm(request.form, funds)
        if not form.validate():
            ctx = _get_transactions_page_context()
            return render_template(
                'transactions.html',
                **ctx,
                form_errors={'asset_add': form.errors},
                form_values={'asset_add': request.form},
                open_modal='addAssetModal',
            ), 400

        # Get cleaned data
        data = form.get_cleaned_data()

        # Add asset using service
        asset = transaction_service.add_asset(
            fund_id=data['fund_id'],
            symbol=data['symbol']
        )

        flash(SuccessMessages.ASSET_ADDED, 'success')

    except ValueError as e:
        flash(get_error_message(e), 'error')

    except Exception as e:
        db.session.rollback()
        flash('Operation failed', 'error')

    return redirect(url_for('transactions.transaction_list'))


@transactions_bp.route('/assets/delete', methods=['POST'])
def asset_delete():
    """Delete tracked asset."""
    try:
        # Get services
        transaction_service, _, _, _ = get_services()

        # Validate form
        form = AssetDeleteForm(request.form)
        if not form.validate():
            if is_ajax_request():
                return json_response(False, error='Invalid request')
            flash('Invalid request', 'error')
            return redirect(url_for('transactions.transaction_list'))

        # Get cleaned data
        data = form.get_cleaned_data()

        # Delete asset using service
        transaction_service.delete_asset(
            fund_id=data['fund_id'],
            symbol=data['symbol']
        )

        if is_ajax_request():
            return json_response(True, message=SuccessMessages.ASSET_DELETED)
        flash(SuccessMessages.ASSET_DELETED, 'success')

    except ValueError as e:
        if is_ajax_request():
            return json_response(False, error=get_error_message(e))
        flash(get_error_message(e), 'error')

    except Exception as e:
        db.session.rollback()
        if is_ajax_request():
            return json_response(False, error='Operation failed')
        flash('Operation failed', 'error')

    return redirect(url_for('transactions.transaction_list'))
