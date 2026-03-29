"""FreshBooks OAuth connector."""
import os
import json
import urllib.parse
import urllib.request
import logging
from datetime import datetime, timedelta
from typing import Dict, List
from .base import BaseConnector

logger = logging.getLogger(__name__)

FB_AUTH_URL = 'https://auth.freshbooks.com/oauth/authorize'
FB_TOKEN_URL = 'https://api.freshbooks.com/auth/oauth/token'
FB_API = 'https://api.freshbooks.com'


class FreshBooksConnector(BaseConnector):
    platform = 'freshbooks'

    def __init__(self):
        self.client_id = os.environ.get('FRESHBOOKS_CLIENT_ID', '')
        self.client_secret = os.environ.get('FRESHBOOKS_CLIENT_SECRET', '')
        self.redirect_uri = os.environ.get('LEAKLOCK_DOMAIN', 'http://localhost:5050') + '/connect/freshbooks/callback'

    def get_auth_url(self, state: str) -> str:
        params = {
            'client_id': self.client_id,
            'response_type': 'code',
            'redirect_uri': self.redirect_uri,
            'state': state,
        }
        return FB_AUTH_URL + '?' + urllib.parse.urlencode(params)

    def exchange_code(self, code: str, state: str) -> Dict:
        data = json.dumps({
            'grant_type': 'authorization_code',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'code': code,
            'redirect_uri': self.redirect_uri,
        }).encode()
        req = urllib.request.Request(FB_TOKEN_URL, data=data, headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req) as r:
            result = json.loads(r.read())
        access_token = result.get('access_token', '')
        account_id = ''
        account_name = 'FreshBooks Account'
        try:
            req2 = urllib.request.Request(f'{FB_API}/auth/api/v1/users/me', headers={'Authorization': f'Bearer {access_token}'})
            with urllib.request.urlopen(req2) as r2:
                me = json.loads(r2.read())
            memberships = me.get('response', {}).get('roles', [])
            if memberships:
                account_id = str(memberships[0].get('accountid', ''))
                account_name = memberships[0].get('business', {}).get('name', 'FreshBooks Account')
        except Exception:
            pass
        return {
            'access_token': access_token,
            'refresh_token': result.get('refresh_token', ''),
            'expires_in': result.get('expires_in', 3600),
            'realm_id': account_id,
            'account_name': account_name,
        }

    def refresh_access_token(self, refresh_token: str) -> Dict:
        data = json.dumps({
            'grant_type': 'refresh_token',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'refresh_token': refresh_token,
        }).encode()
        req = urllib.request.Request(FB_TOKEN_URL, data=data, headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req) as r:
            result = json.loads(r.read())
        return {
            'access_token': result.get('access_token', ''),
            'refresh_token': result.get('refresh_token', refresh_token),
            'expires_in': result.get('expires_in', 3600),
        }

    def fetch_transactions(self, access_token: str, realm_id: str = None, days_back: int = 365) -> List[Dict]:
        since = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
        url = f'{FB_API}/accounting/account/{realm_id}/invoices/invoices?search[date_min]={since}&per_page=200'
        req = urllib.request.Request(url, headers={'Authorization': f'Bearer {access_token}', 'Content-Type': 'application/json', 'Api-Version': 'alpha'})
        try:
            with urllib.request.urlopen(req) as r:
                data = json.loads(r.read())
        except Exception as e:
            logger.error(f'FreshBooks fetch error: {e}')
            return []
        rows = []
        for inv in data.get('response', {}).get('result', {}).get('invoices', []):
            rows.append({
                'date': inv.get('create_date', ''),
                'amount': float(inv.get('amount', {}).get('amount', 0)),
                'customer_id': str(inv.get('customerid', '')),
                'status': inv.get('payment_status', '').lower(),
                'description': inv.get('notes', ''),
                'invoice_id': str(inv.get('invoiceid', '')),
                'discount': float(inv.get('discount_value', 0)),
            })
        return rows
