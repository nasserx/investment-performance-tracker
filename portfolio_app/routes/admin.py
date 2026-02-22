"""Admin blueprint — user management for admins."""

import logging
from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from portfolio_app.services import get_services

logger = logging.getLogger(__name__)

admin_bp = Blueprint('admin', __name__)


def admin_required(f):
    """Decorator: allow access only to admin users."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)
    return decorated


@admin_bp.route('/users')
@login_required
@admin_required
def users():
    """Admin user list page."""
    svc = get_services()
    all_users = svc.user_repo.get_all()
    return render_template('admin/users.html', users=all_users)


@admin_bp.route('/users/<int:user_id>/reset-password', methods=['POST'])
@login_required
@admin_required
def reset_password(user_id):
    """Reset a user's password and display the temporary password."""
    svc = get_services()
    try:
        temp_password = svc.auth_service.reset_password(user_id)
        flash(
            f'Password reset successfully. Temporary password: {temp_password}',
            'warning'
        )
    except ValueError as e:
        flash(str(e), 'error')
    except Exception:
        logger.exception('Admin reset password failed for user %s', user_id)
        flash('Operation failed. Please try again.', 'error')

    return redirect(url_for('admin.users'))


@admin_bp.route('/users/<int:user_id>/toggle-admin', methods=['POST'])
@login_required
@admin_required
def toggle_admin(user_id):
    """Toggle admin status for a user."""
    svc = get_services()
    try:
        user = svc.auth_service.toggle_admin(user_id, current_user)
        status = 'granted' if user.is_admin else 'revoked'
        flash(f'Admin access {status} for {user.username}.', 'success')
    except ValueError as e:
        flash(str(e), 'error')
    except Exception:
        logger.exception('Toggle admin failed for user %s', user_id)
        flash('Operation failed.', 'error')

    return redirect(url_for('admin.users'))


@admin_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    """Delete a user account."""
    svc = get_services()
    try:
        svc.auth_service.delete_user(user_id, current_user)
        flash('User deleted successfully.', 'success')
    except ValueError as e:
        flash(str(e), 'error')
    except Exception:
        logger.exception('Admin delete user failed for user %s', user_id)
        flash('Operation failed.', 'error')

    return redirect(url_for('admin.users'))


@admin_bp.errorhandler(403)
def forbidden(e):
    return render_template('auth/login.html',
                           form_errors={'__all__': 'Access denied. Admins only.'},
                           form_values={}), 403
