import os
from portfolio_app import create_app, db

app = create_app()


def main():
    """Initialize database and run the application."""
    with app.app_context():
        db.create_all()

    debug = os.environ.get('FLASK_DEBUG', '0').lower() in ('1', 'true', 'yes')
    host = os.environ.get('FLASK_HOST', '127.0.0.1')
    port = int(os.environ.get('FLASK_PORT', '5000'))
    app.run(debug=debug, host=host, port=port)


if __name__ == '__main__':
    main()
