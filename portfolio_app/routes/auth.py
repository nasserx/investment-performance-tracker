"""Auth blueprint — login, register, logout, change password."""

import logging
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from portfolio_app.services import get_services
from portfolio_app.forms.auth_forms import LoginForm, RegisterForm, ChangePasswordForm

logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Login page."""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))

    form_errors = {}
    form_values = {}

    if request.method == 'POST':
        form = LoginForm(request.form)
        if form.validate():
            data = form.get_cleaned_data()
            svc = get_services()
            user = svc.auth_service.authenticate(data['username'], data['password'])
            if user:
                remember = request.form.get('remember') == 'on'
                login_user(user, remember=remember)
                next_page = request.args.get('next')
                return redirect(next_page or url_for('dashboard.index'))
            else:
                form_errors['__all__'] = 'Invalid username or password.'
                form_values = request.form
        else:
            form_errors = form.errors
            form_values = request.form

    return render_template(
        'auth/login.html',
        form_errors=form_errors,
        form_values=form_values,
    )


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Register new account page."""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))

    form_errors = {}
    form_values = {}

    if request.method == 'POST':
        svc = get_services()

        def username_taken(username: str) -> bool:
            return svc.user_repo.get_by_username(username) is not None

        form = RegisterForm(request.form, check_username_taken=username_taken)
        if form.validate():
            data = form.get_cleaned_data()
            try:
                user, _ = svc.auth_service.register(data['username'], data['password'])
                login_user(user)
                return redirect(url_for('dashboard.index'))
            except ValueError as e:
                form_errors['__all__'] = str(e)
                form_values = request.form
            except Exception:
                logger.exception('Registration failed')
                form_errors['__all__'] = 'Registration failed. Please try again.'
                form_values = request.form
        else:
            form_errors = form.errors
            form_values = request.form

    return render_template(
        'auth/register.html',
        form_errors=form_errors,
        form_values=form_values,
    )


@auth_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    """Logout (CSRF-protected POST)."""
    logout_user()
    return redirect(url_for('auth.login'))


@auth_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    """Change password page."""
    form_errors = {}
    form_values = {}

    if request.method == 'POST':
        form = ChangePasswordForm(request.form)
        if form.validate():
            data = form.get_cleaned_data()
            svc = get_services()
            try:
                svc.auth_service.change_password(
                    current_user,
                    data['current_password'],
                    data['new_password'],
                )
                flash('Password changed successfully.', 'success')
                return redirect(url_for('dashboard.index'))
            except ValueError as e:
                form_errors['current_password'] = str(e)
                form_values = request.form
            except Exception:
                logger.exception('Password change failed')
                form_errors['__all__'] = 'An error occurred. Please try again.'
                form_values = request.form
        else:
            form_errors = form.errors
            form_values = request.form

    return render_template(
        'auth/change_password.html',
        form_errors=form_errors,
        form_values=form_values,
    )
