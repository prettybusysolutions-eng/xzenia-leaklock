"""Square OAuth connector."""
import os
import json
import urllib.parse
import urllib.request
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List
from .base import BaseConnector

logger = logging.getLogger(__name__)

SQUARE_AUTH_URL = 'https://connect.squareup.com/oauth2/authorize'
SQUARE_TOKEN_URL = 'https://connect.squareup.com/oauth2/token'
SQUARE_API = 'https://connect.squareup.com/v2'


class SquareConnector(BaseConnector):
    platform = 'square'

    def __init__(self):
        self.client_id = os.environ.get('SQUARE_APP_ID', '')
        self.client_secret = os.environ.get('SQUARE_APP_SECRET', '')
        self.redirect_uri = os.environ.get('LEAKLOCK_DOMAIN', 'http://localhost:5050') + '/connect/square/callback'

    def get_auth_url(self, state: str) -> str:
        params = {
            'client_id': self.client_id,
            'scope': 'PAYMENTS_READ ORDERS_READ CUSTOMERS_READ INVOICES_READ',
            'session': 'false',
            'state': state,
        }
        return SQUARE_AUTH_URL + '?' + urllib.parse.urlencode(params)

    def exchange_code(self, code: str, state: str) -> Dict:
        data = json.dumps({
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': self.redirect_uri,
        }).encode()
        req = urllib.request.Request(SQUARE_TOKEN_URL, data=data, headers={'Content-Type': 'application/json', 'Square-Version': '2024-01-18'})
        with urllib.request.urlopen(req) as r:
            result = json.loads(r.read())
        return {
            'access_token': result.get('access_token', ''),
            'refresh_token': result.get('refresh_token', ''),
            'expires_in': 2592000,
            'realm_id': result.get('merchant_id', ''),
            'account_name': 'Square Account',
        }

    def refresh_access_token(self, refresh_token: str) -> Dict:
        data = json.dumps({
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token,
        }).encode()
        req = urllib.request.Request(SQUARE_TOKEN_URL, data=data, headers={'Content-Type': 'application/json', 'Square-Version': '2024-01-18'})
        with urllib.request.urlopen(req) as r:
            result = json.loads(r.read())
        return {
            'access_token': result.get('access_token', ''),
            'refresh_token': result.get('refresh_token', refresh_token),
            'expires_in': 2592000,
        }

    def fetch_transactions(self, access_token: str, realm_id: str = None, days_back: int = 365) -> List[Dict]:
        since = (datetime.now(timezone.utc) - timedelta(days=days_back)).strftime('%Y-%m-%dT%H:%M:%SZ')
        url = f'{SQUARE_API}/payments?begin_time={since}&limit=200'
        req = urllib.request.Request(url, headers={'Authorization': f'Bearer {access_token}', 'Square-Version': '2024-01-18'})
        try:
            with urllib.request.urlopen(req) as r:
                result = json.loads(r.read())
        except Exception as e:
            logger.error(f'Square fetch error: {e}')
            return []
        rows = []
        for p in result.get('payments', []):
            amt = p.get('amount_money', {})
            rows.append({
                'date': p.get('created_at', '')[:10],
                'amount': amt.get('amount', 0) / 100,
                'customer_id': p.get('customer_id', ''),
                'status': p.get('status', '').lower(),
                'description': p.get('note', ''),
                'invoice_id': p.get('order_id', ''),
                'refund': sum(r.get('amount_money', {}).get('amount', 0) for r in p.get('refunds', [])) / 100,
            })
        return rows
