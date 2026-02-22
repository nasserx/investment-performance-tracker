from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect, CSRFError
from flask_login import LoginManager
from config import Config
from portfolio_app.utils import fmt_decimal, fmt_money

db = SQLAlchemy()
csrf = CSRFProtect()
login_manager = LoginManager()


def _run_migrations(app):
    """Apply incremental schema changes that SQLAlchemy create_all() cannot handle."""
    import sqlalchemy as sa
    with app.app_context():
        with db.engine.connect() as conn:
            inspector = sa.inspect(db.engine)

            capital_cols = {c['name'] for c in inspector.get_columns('capital')}

            # 1. Add user_id column if missing
            if 'user_id' not in capital_cols:
                conn.execute(sa.text(
                    'ALTER TABLE capital ADD COLUMN user_id INTEGER REFERENCES "user"(id)'
                ))
                conn.commit()
                capital_cols.add('user_id')

            # 2. Rename amount_usd → amount if still using the old name
            if 'amount_usd' in capital_cols and 'amount' not in capital_cols:
                conn.execute(sa.text(
                    'ALTER TABLE capital RENAME COLUMN amount_usd TO amount'
                ))
                conn.commit()


def create_app(config_class=Config):
    """Application factory pattern."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
    csrf.init_app(app)
    login_manager.init_app(app)

    # Flask-Login configuration
    login_manager.login_view = 'auth.login'
    login_manager.login_message = ''

    @login_manager.user_loader
    def load_user(user_id: str):
        from portfolio_app.models.user import User
        return User.query.get(int(user_id))

    @app.errorhandler(CSRFError)
    def _handle_csrf_error(e: CSRFError):
        from flask import flash, redirect, request, url_for, jsonify

        # Return JSON for AJAX requests
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
            return jsonify({'success': False, 'error': 'Session expired. Please refresh the page.'}), 400

        try:
            flash("Security check failed (CSRF token missing/invalid). Refresh the page then try again.", "warning")
        except Exception:
            pass

        ref = request.referrer
        if ref:
            return redirect(ref)
        return redirect(url_for("dashboard.index"))

    # Template filters
    app.jinja_env.filters['fmt_decimal'] = fmt_decimal
    app.jinja_env.filters['fmt_money'] = fmt_money

    # Inject category icons into all templates
    @app.context_processor
    def inject_category_icons():
        return {
            'category_icons': app.config.get('ASSET_CATEGORY_ICONS', {}),
            'category_icon_default': app.config.get('ASSET_CATEGORY_ICON_DEFAULT', ('bi-folder', 'text-secondary')),
        }

    # Create tables and run migrations
    with app.app_context():
        # Import all models so SQLAlchemy knows about them before create_all()
        from portfolio_app.models import User, Fund, Transaction, Asset, FundEvent  # noqa: F401
        db.create_all()
        _run_migrations(app)

    # Register blueprints
    from portfolio_app.routes import register_blueprints
    register_blueprints(app)

    return app
