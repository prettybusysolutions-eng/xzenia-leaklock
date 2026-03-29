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

# DB
DB_CONFIG = {
    'host': os.environ.get('DB_HOST', 'localhost'),
    'dbname': os.environ.get('DB_NAME', 'nexus'),
    'user': os.environ.get('DB_USER', 'marcuscoarchitect'),
    'password': os.environ.get('DB_PASSWORD', ''),
    'port': int(os.environ.get('DB_PORT', 5432)),
}

# Upload
UPLOAD_FOLDER = '/tmp/leaklock_uploads'
CACHE_TTL = 3600  # seconds
SCAN_RESULT_TTL = 7200  # seconds

# Rate limiting
RATE_LIMITS = {
    'default': "200 per day",
    'upload': "10 per hour",
}
