"""LeakLock Flask Application Factory."""
import os
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
from dotenv import load_dotenv

load_dotenv()

from flask import Flask
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from routes.connect import connect_bp
from routes.stripe_scan import stripe_scan_bp


def create_app():
    """Create and configure the Flask application."""
    app = Flask(__name__)
    
    # Config
    from config import SECRET_KEY, MAX_FILE_SIZE
    app.config['SECRET_KEY'] = SECRET_KEY
    app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE
    
    # CSRF protection
    csrf = CSRFProtect(app)
    # Exempt OAuth routes from CSRF checks
    csrf.exempt(connect_bp)
    
    # Rate limiter
    limiter = Limiter(
        key_func=get_remote_address,
        app=app,
        storage_uri="memory://",
        default_limits=["200 per day", "50 per hour"]
    )
    
    # Register blueprints
    from routes import page_bp, api_bp, checkout_bp, webhooks_bp
    from routes.webhooks import stripe_webhook
    # Stripe authenticates the raw body with its signature, not a browser token.
    csrf.exempt(stripe_webhook)
    app.register_blueprint(page_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(checkout_bp)
    app.register_blueprint(webhooks_bp)
    app.register_blueprint(connect_bp)
    app.register_blueprint(stripe_scan_bp)
    
    # Initialize DB pool
    from models.db import (
        get_pool,
        init_payments_table,
        init_webhook_dlq_table,
        init_scan_emails_table,
        init_connections_table,
        init_scan_cache_table,
        init_consequence_tables,
    )
    try:
        get_pool()
        init_payments_table()
        init_webhook_dlq_table()
        init_scan_emails_table()
        init_connections_table()
        init_scan_cache_table()
        init_consequence_tables()
    except Exception as e:
        print(f'[WARN] DB pool init failed: {e}')

    # Initialize API keys table (lazy-loaded on first use, but pre-init here)
    try:
        from routes.api import _init_api_keys_table
        _init_api_keys_table()
    except Exception as e:
        print(f'[WARN] API keys table init failed: {e}')
    
    # Liveness proves the process can answer. Readiness proves required
    # dependencies are available.
    @app.route('/live')
    def live():
        return {'status': 'ok', 'service': 'leaklock'}, 200

    @app.route('/health')
    def health():
        try:
            from models.db import get_pool as current_get_pool
            pool = current_get_pool()
            conn = pool.getconn()
            try:
                with conn.cursor() as cursor:
                    cursor.execute('SELECT 1')
                    cursor.fetchone()
            finally:
                pool.putconn(conn)
        except Exception:
            return {
                'status': 'unavailable',
                'service': 'leaklock',
                'database': 'unavailable',
            }, 503
        return {'status': 'ok', 'service': 'leaklock', 'database': 'ok'}, 200
    
    return app
