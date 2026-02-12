import os
from pathlib import Path

basedir = Path(__file__).parent


class Config:
    """Base configuration"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        f'sqlite:///{basedir / "portfolio.db"}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Security hardening
    WTF_CSRF_ENABLED = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    # If you serve over HTTPS, set this to True (or via env) to harden cookies.
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', '0') in ('1', 'true', 'True')
    
    # Asset categories
    ASSET_CATEGORIES = [
        'Gold',
        'Stocks',
        'ETFs',
        'Crypto'
    ]
    
    # Transaction types
    TRANSACTION_TYPES = ['Buy', 'Sell']
