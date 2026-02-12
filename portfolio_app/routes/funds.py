"""Funds blueprint - Fund management routes."""

from flask import Blueprint, render_template, request, redirect, url_for, flash, g
from decimal import Decimal
import re
from portfolio_app import db
from portfolio_app.models import Fund, FundEvent
from portfolio_app.services import FundService
from portfolio_app.repositories import FundRepository, FundEventRepository
from portfolio_app.forms import (
    FundAddForm,
    FundDepositForm,
    FundWithdrawForm,
    FundEventEditForm,
    FundEventDeleteForm
)
from portfolio_app.utils import get_error_message, get_first_form_error, SuccessMessages, is_ajax_request, json_response
from config import Config

# Create blueprint
funds_bp = Blueprint('funds', __name__)


def get_services():
    """Get service instances (cached per request in g object)."""
    if not hasattr(g, 'funds_services'):
        fund_repo = FundRepository(Fund, db)
        event_repo = FundEventRepository(FundEvent, db)
        fund_service = FundService(fund_repo, event_repo)
        g.funds_services = (fund_service, fund_repo, event_repo)
    return g.funds_services


def _get_funds_page_context():
    """Get context data for funds page."""
    _, fund_repo, event_repo = get_services()
    funds = fund_repo.get_all()
    available_categories = fund_repo.get_available_categories(Config.ASSET_CATEGORIES)

    funds_data = []
    for fund in funds:
        events = event_repo.get_by_fund_id(fund.id)

        # One-time backfill for legacy databases
        if not events:
            try:
                backfill = FundEvent(
                    fund_id=fund.id,
                    event_type='Initial',
                    amount_delta=Decimal(str(fund.amount or 0)),
                    date=fund.created_at,
                    notes=None,
                )
                db.session.add(backfill)
                db.session.commit()
                events = [backfill]
            except Exception:
                db.session.rollback()

        group_id = re.sub(r'[^A-Za-z0-9_\-]+', '_', f"{fund.id}-{fund.category}")
        funds_data.append({
            'fund': fund,
            'events': events,
            'group_id': group_id,
        })

    return {
        'funds': funds,
        'funds_data': funds_data,
        'available_categories': available_categories,
    }


@funds_bp.route('/')
def funds_list():
    """Funds management page."""
    ctx = _get_funds_page_context()
    return render_template(
        'funds.html',
        **ctx,
        form_errors={},
        form_values={},
        open_modal=None,
        open_modal_payload=None,
    )


@funds_bp.route('/add', methods=['POST'])
def funds_add():
    """Add new fund."""
    try:
        # Get services
        fund_service, fund_repo, _ = get_services()

        # Get available categories
        available_categories = fund_repo.get_available_categories(Config.ASSET_CATEGORIES)

        # Validate form
        form = FundAddForm(request.form, available_categories)
        if not form.validate():
            if is_ajax_request():
                return json_response(False, error=get_first_form_error(form.errors))

            ctx = _get_funds_page_context()
            return render_template(
                'funds.html',
                **ctx,
                form_errors={'funds_add': form.errors},
                form_values={'funds_add': request.form},
                open_modal='addFundEntryModal',
            ), 400

        # Get cleaned data
        data = form.get_cleaned_data()

        # Create fund using service
        fund = fund_service.create_fund(
            category=data['category'],
            amount=data['amount'],
            notes='Initial funding'
        )

        if is_ajax_request():
            return json_response(True, message=SuccessMessages.FUND_CREATED)

        flash(SuccessMessages.FUND_CREATED, 'success')
        return redirect(url_for('funds.funds_list'))

    except ValueError as e:
        if is_ajax_request():
            return json_response(False, error=get_error_message(e))

        ctx = _get_funds_page_context()
        return render_template(
            'funds.html',
            **ctx,
            form_errors={'funds_add': {'__all__': str(e)}},
            form_values={'funds_add': request.form},
            open_modal='addFundEntryModal',
        ), 400

    except Exception as e:
        db.session.rollback()

        if is_ajax_request():
            return json_response(False, error='Operation failed')

        ctx = _get_funds_page_context()
        return render_template(
            'funds.html',
            **ctx,
            form_errors={'funds_add': {'__all__': 'Operation failed'}},
            form_values={'funds_add': request.form},
            open_modal='addFundEntryModal',
        ), 400


@funds_bp.route('/delete/<int:id>', methods=['POST'])
def funds_delete(id):
    """Delete fund."""
    try:
        fund_service, _, _ = get_services()
        category = fund_service.delete_fund(id)
        flash(SuccessMessages.FUND_DELETED, 'success')

    except ValueError as e:
        flash(get_error_message(e), 'error')

    except Exception as e:
        db.session.rollback()
        flash('Operation failed', 'error')

    return redirect(url_for('funds.funds_list'))


@funds_bp.route('/deposit/<int:id>', methods=['POST'])
def funds_deposit(id):
    """Deposit funds to category."""
    try:
        # Get services
        fund_service, _, _ = get_services()

        # Validate form
        form = FundDepositForm(request.form, id)
        if not form.validate():
            if is_ajax_request():
                return json_response(False, error=get_first_form_error(form.errors))

            ctx = _get_funds_page_context()
            return render_template(
                'funds.html',
                **ctx,
                form_errors={'funds_deposit': form.errors},
                form_values={'funds_deposit': request.form},
                open_modal='depositFundModal',
                open_modal_payload={'fund_id': id},
            ), 400

        # Get cleaned data
        data = form.get_cleaned_data()

        # Deposit using service
        fund = fund_service.deposit_funds(
            fund_id=data['fund_id'],
            amount_delta=data['amount_delta'],
            notes=data.get('notes')
        )

        if is_ajax_request():
            return json_response(True, message=SuccessMessages.DEPOSIT_COMPLETED)

        flash(SuccessMessages.DEPOSIT_COMPLETED, 'success')
        return redirect(url_for('funds.funds_list'))

    except ValueError as e:
        if is_ajax_request():
            return json_response(False, error=get_error_message(e))

        flash(get_error_message(e), 'error')
        return redirect(url_for('funds.funds_list'))

    except Exception as e:
        db.session.rollback()

        if is_ajax_request():
            return json_response(False, error='Operation failed')

        flash('Operation failed', 'error')
        return redirect(url_for('funds.funds_list'))


@funds_bp.route('/withdraw/<int:id>', methods=['POST'])
def funds_withdraw(id):
    """Withdraw funds from category."""
    try:
        # Get services
        fund_service, _, _ = get_services()

        # Validate form
        form = FundWithdrawForm(request.form, id)
        if not form.validate():
            if is_ajax_request():
                return json_response(False, error=get_first_form_error(form.errors))

            ctx = _get_funds_page_context()
            return render_template(
                'funds.html',
                **ctx,
                form_errors={'funds_withdraw': form.errors},
                form_values={'funds_withdraw': request.form},
                open_modal='withdrawFundModal',
                open_modal_payload={'fund_id': id},
            ), 400

        # Get cleaned data
        data = form.get_cleaned_data()

        # Withdraw using service
        fund = fund_service.withdraw_funds(
            fund_id=data['fund_id'],
            amount_delta=data['amount_delta'],
            notes=data.get('notes')
        )

        if is_ajax_request():
            return json_response(True, message=SuccessMessages.WITHDRAWAL_COMPLETED)

        flash(SuccessMessages.WITHDRAWAL_COMPLETED, 'success')
        return redirect(url_for('funds.funds_list'))

    except ValueError as e:
        if is_ajax_request():
            return json_response(False, error=get_error_message(e))

        flash(get_error_message(e), 'error')
        return redirect(url_for('funds.funds_list'))

    except Exception as e:
        db.session.rollback()

        if is_ajax_request():
            return json_response(False, error='Operation failed')

        flash('Operation failed', 'error')
        return redirect(url_for('funds.funds_list'))


@funds_bp.route('/events/edit/<int:event_id>', methods=['POST'])
def funds_event_edit(event_id):
    """Edit fund event."""
    try:
        # Get services
        fund_service, _, event_repo = get_services()

        # Get current event
        event = event_repo.get_by_id(event_id)
        if not event:
            flash('Event not found', 'error')
            return redirect(url_for('funds.funds_list'))

        # Validate form
        form = FundEventEditForm(request.form, event_id, event.event_type)
        if not form.validate():
            ctx = _get_funds_page_context()
            return render_template(
                'funds.html',
                **ctx,
                form_errors={'fund_event_edit': form.errors},
                form_values={'fund_event_edit': request.form},
                open_modal='editFundEventModal',
                open_modal_payload={'event_id': event_id},
            ), 400

        # Get cleaned data
        data = form.get_cleaned_data()

        # Update using service
        fund_service.update_fund_event(
            event_id=data['event_id'],
            amount_delta=data['amount_delta'],
            notes=data.get('notes'),
            date=data.get('date')
        )

        flash(SuccessMessages.EVENT_UPDATED, 'success')

    except ValueError as e:
        flash(get_error_message(e), 'error')

    except Exception as e:
        db.session.rollback()
        flash('Operation failed', 'error')

    return redirect(url_for('funds.funds_list'))


@funds_bp.route('/events/delete/<int:event_id>', methods=['POST'])
def funds_event_delete(event_id):
    """Delete fund event."""
    try:
        # Get services
        fund_service, _, event_repo = get_services()

        # Get current event
        event = event_repo.get_by_id(event_id)
        if not event:
            flash('Event not found', 'error')
            return redirect(url_for('funds.funds_list'))

        # Validate (check if it's not Initial event)
        form = FundEventDeleteForm(request.form, event_id, event.event_type)
        if not form.validate():
            flash(get_first_form_error(form.errors), 'error')
            return redirect(url_for('funds.funds_list'))

        # Delete using service
        fund_service.delete_fund_event(event_id)

        flash(SuccessMessages.EVENT_DELETED, 'success')

    except ValueError as e:
        flash(get_error_message(e), 'error')

    except Exception as e:
        db.session.rollback()
        flash('Operation failed', 'error')

    return redirect(url_for('funds.funds_list'))
