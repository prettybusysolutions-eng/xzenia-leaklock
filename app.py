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
        init_scan_emails_table,
        init_connections_table,
        init_scan_cache_table,
    )
    try:
        get_pool()
        init_payments_table()
        init_scan_emails_table()
        init_connections_table()
        init_scan_cache_table()
    except Exception as e:
        print(f'[WARN] DB pool init failed: {e}')
    
    # Health check route
    @app.route('/health')
    def health():
        return 'OK'
    
    return app
