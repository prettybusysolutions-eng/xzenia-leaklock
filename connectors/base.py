"""Base connector class and shared utilities."""
import os
import logging
from typing import Dict, List
from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)

_fernet_key = os.environ.get('TOKEN_ENCRYPTION_KEY', '')
_fernet = None


def get_fernet():
    global _fernet, _fernet_key
    if _fernet is None:
        if not _fernet_key:
            import hashlib
            import base64
            secret = os.environ.get('FLASK_SECRET_KEY', 'leaklock-dev-key-change-in-prod-2026')
            key_bytes = hashlib.sha256(secret.encode()).digest()
            _fernet_key = base64.urlsafe_b64encode(key_bytes).decode()
        _fernet = Fernet(_fernet_key.encode() if isinstance(_fernet_key, str) else _fernet_key)
    return _fernet


def encrypt_token(token: str) -> str:
    return get_fernet().encrypt(token.encode()).decode()


def decrypt_token(enc: str) -> str:
    return get_fernet().decrypt(enc.encode()).decode()


def normalize_to_scan_rows(transactions: List[Dict]) -> List[Dict]:
    """Normalize platform-specific transaction data into LeakLock's standard row format."""
    rows = []
    for t in transactions:
        row = {
            'date': t.get('date', ''),
            'amount': str(t.get('amount', 0)),
            'customer_id': str(t.get('customer_id', '')),
            'status': t.get('status', 'unknown'),
            'description': t.get('description', ''),
            'invoice_id': t.get('invoice_id', ''),
        }
        for k in ['discount', 'tax', 'refund', 'category', 'payment_method']:
            if k in t:
                row[k] = str(t[k])
        rows.append(row)
    return rows


class BaseConnector:
    """Base class for all OAuth connectors."""
    platform = 'base'

    def __init__(self):
        self.client_id = os.environ.get(f'{self.platform.upper()}_CLIENT_ID', '')
        self.client_secret = os.environ.get(f'{self.platform.upper()}_CLIENT_SECRET', '')
        self.redirect_uri = os.environ.get('LEAKLOCK_DOMAIN', 'http://localhost:5050') + f'/connect/{self.platform}/callback'

    def get_auth_url(self, state: str) -> str:
        raise NotImplementedError

    def exchange_code(self, code: str, state: str) -> Dict:
        raise NotImplementedError

    def refresh_access_token(self, refresh_token: str) -> Dict:
        raise NotImplementedError

    def fetch_transactions(self, access_token: str, realm_id: str = None, days_back: int = 365) -> List[Dict]:
        raise NotImplementedError

    def is_configured(self) -> bool:
        return bool(self.client_id and self.client_secret)
