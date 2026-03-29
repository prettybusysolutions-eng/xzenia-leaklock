"""Stripe Connect OAuth connector."""
import os
import json
import urllib.parse
import urllib.request
import logging
from datetime import datetime, timedelta
from typing import Dict, List
from .base import BaseConnector

logger = logging.getLogger(__name__)

STRIPE_AUTH_URL = 'https://connect.stripe.com/oauth/authorize'
STRIPE_TOKEN_URL = 'https://connect.stripe.com/oauth/token'
STRIPE_API = 'https://api.stripe.com/v1'


class StripeConnector(BaseConnector):
    platform = 'stripe'

    def __init__(self):
        self.client_id = os.environ.get('STRIPE_CLIENT_ID', '')
        self.client_secret = os.environ.get('STRIPE_SECRET_KEY', '')
        self.redirect_uri = os.environ.get('LEAKLOCK_DOMAIN', 'http://localhost:5050') + '/connect/stripe/callback'

    def get_auth_url(self, state: str) -> str:
        params = {
            'response_type': 'code',
            'client_id': self.client_id,
            'scope': 'read_only',
            'redirect_uri': self.redirect_uri,
            'state': state,
        }
        return STRIPE_AUTH_URL + '?' + urllib.parse.urlencode(params)

    def exchange_code(self, code: str, state: str) -> Dict:
        data = urllib.parse.urlencode({
            'grant_type': 'authorization_code',
            'code': code,
            'client_secret': self.client_secret,
        }).encode()
        req = urllib.request.Request(STRIPE_TOKEN_URL, data=data, headers={'Content-Type': 'application/x-www-form-urlencoded'})
        with urllib.request.urlopen(req) as r:
            result = json.loads(r.read())
        return {
            'access_token': result.get('access_token', ''),
            'refresh_token': result.get('refresh_token', ''),
            'expires_in': 0,
            'realm_id': result.get('stripe_user_id', ''),
            'account_name': result.get('stripe_publishable_key', 'Stripe Account'),
        }

    def refresh_access_token(self, refresh_token: str) -> Dict:
        return {
            'access_token': refresh_token,
            'refresh_token': refresh_token,
            'expires_in': 0,
        }

    def fetch_transactions(self, access_token: str, realm_id: str = None, days_back: int = 365) -> List[Dict]:
        since = int((datetime.now() - timedelta(days=days_back)).timestamp())
        url = f"{STRIPE_API}/charges?limit=100&created[gte]={since}"
        req = urllib.request.Request(url, headers={'Authorization': f'Bearer {access_token}'})
        try:
            with urllib.request.urlopen(req) as r:
                data = json.loads(r.read())
        except Exception as e:
            logger.error(f'Stripe fetch error: {e}')
            return []
        rows = []
        for ch in data.get('data', []):
            rows.append({
                'date': datetime.fromtimestamp(ch.get('created', 0)).strftime('%Y-%m-%d'),
                'amount': ch.get('amount', 0) / 100,
                'customer_id': ch.get('customer', ''),
                'status': ch.get('status', ''),
                'description': ch.get('description', ''),
                'invoice_id': ch.get('invoice', ''),
                'refund': ch.get('amount_refunded', 0) / 100,
            })
        return rows
