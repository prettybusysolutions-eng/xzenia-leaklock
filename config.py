"""LeakLock Configuration"""
import os
from dotenv import load_dotenv

load_dotenv()

# Flask
SECRET_KEY = os.environ.get('FLASK_SECRET_KEY', 'leaklock-dev-key-change-in-prod-2026')
HOST = '0.0.0.0'
PORT = int(os.environ.get('PORT', 5050))

# File limits
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
ASYNC_THRESHOLD = 5 * 1024 * 1024  # 5MB goes async (future use)
ALLOWED_EXTENSIONS = {'.csv', '.xlsx', '.xls', '.tsv'}
ALLOWED_MIME_TYPES = {
    'text/csv',
    'text/plain',
    'application/csv',
    'application/vnd.ms-excel',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'application/octet-stream',
    'application/zip',  # xlsx is a ZIP
}

# Stripe
STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY', '')
STRIPE_WEBHOOK_SECRET = os.environ.get('STRIPE_WEBHOOK_SECRET', '')
LEAKLOCK_DOMAIN = os.environ.get('LEAKLOCK_DOMAIN', 'http://localhost:5050')
STRIPE_WEBHOOK_ID = 'we_1TFKiIAc6hzX3Jk19nbCEBYq'

# DB — supports both local dev (individual vars) and Render (DATABASE_URL)
def _build_db_config():
    db_url = os.environ.get('DATABASE_URL', '')
    if db_url:
        # Parse postgresql://user:pass@host:port/dbname
        import urllib.parse
        parsed = urllib.parse.urlparse(db_url)
        return {
            'host': parsed.hostname or 'localhost',
            'dbname': parsed.path.lstrip('/') or 'leaklock',
            'user': parsed.username or 'render',
            'password': parsed.password or '',
            'port': parsed.port or 5432,
        }
    return {
        'host': os.environ.get('DB_HOST', 'localhost'),
        'dbname': os.environ.get('DB_NAME', 'nexus'),
        'user': os.environ.get('DB_USER', 'marcuscoarchitect'),
        'password': os.environ.get('DB_PASSWORD', ''),
        'port': int(os.environ.get('DB_PORT', 5432)),
    }

DB_CONFIG = _build_db_config()

# Upload
UPLOAD_FOLDER = '/tmp/leaklock_uploads'
CACHE_TTL = 3600  # seconds
SCAN_RESULT_TTL = 7200  # seconds

# Rate limiting
RATE_LIMITS = {
    'default': "200 per day",
    'upload': "10 per hour",
}
