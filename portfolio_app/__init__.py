from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect, CSRFError
from config import Config
from portfolio_app.utils import fmt_decimal, fmt_money

db = SQLAlchemy()
csrf = CSRFProtect()


def create_app(config_class=Config):
    """Application factory pattern."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
    csrf.init_app(app)

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
    
    # Register blueprints
    from portfolio_app.routes import register_blueprints
    register_blueprints(app)
    
    return app
