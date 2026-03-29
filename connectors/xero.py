"""Xero OAuth connector."""
import os
import json
import urllib.parse
import urllib.request
import logging
import base64
from datetime import datetime, timedelta
from typing import Dict, List
from .base import BaseConnector

logger = logging.getLogger(__name__)

XERO_AUTH_URL = 'https://login.xero.com/identity/connect/authorize'
XERO_TOKEN_URL = 'https://identity.xero.com/connect/token'
XERO_CONNECTIONS_URL = 'https://api.xero.com/connections'
XERO_API = 'https://api.xero.com/api.xro/2.0'


class XeroConnector(BaseConnector):
    platform = 'xero'

    def __init__(self):
        self.client_id = os.environ.get('XERO_CLIENT_ID', '')
        self.client_secret = os.environ.get('XERO_CLIENT_SECRET', '')
        self.redirect_uri = os.environ.get('LEAKLOCK_DOMAIN', 'http://localhost:5050') + '/connect/xero/callback'

    def get_auth_url(self, state: str) -> str:
        params = {
            'response_type': 'code',
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'scope': 'openid profile email accounting.transactions accounting.contacts offline_access',
            'state': state,
        }
        return XERO_AUTH_URL + '?' + urllib.parse.urlencode(params)

    def exchange_code(self, code: str, state: str) -> Dict:
        credentials = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode()).decode()
        data = urllib.parse.urlencode({'grant_type': 'authorization_code', 'code': code, 'redirect_uri': self.redirect_uri}).encode()
        req = urllib.request.Request(XERO_TOKEN_URL, data=data, headers={
            'Authorization': f'Basic {credentials}',
            'Content-Type': 'application/x-www-form-urlencoded',
        })
        with urllib.request.urlopen(req) as r:
            result = json.loads(r.read())
        access_token = result.get('access_token', '')
        realm_id = ''
        account_name = 'Xero Organisation'
        try:
            req2 = urllib.request.Request(XERO_CONNECTIONS_URL, headers={'Authorization': f'Bearer {access_token}', 'Content-Type': 'application/json'})
            with urllib.request.urlopen(req2) as r2:
                conns = json.loads(r2.read())
            if conns:
                realm_id = conns[0].get('tenantId', '')
                account_name = conns[0].get('tenantName', 'Xero Organisation')
        except Exception:
            pass
        return {
            'access_token': access_token,
            'refresh_token': result.get('refresh_token', ''),
            'expires_in': result.get('expires_in', 1800),
            'realm_id': realm_id,
            'account_name': account_name,
        }

    def refresh_access_token(self, refresh_token: str) -> Dict:
        credentials = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode()).decode()
        data = urllib.parse.urlencode({'grant_type': 'refresh_token', 'refresh_token': refresh_token}).encode()
        req = urllib.request.Request(XERO_TOKEN_URL, data=data, headers={
            'Authorization': f'Basic {credentials}',
            'Content-Type': 'application/x-www-form-urlencoded',
        })
        with urllib.request.urlopen(req) as r:
            result = json.loads(r.read())
        return {
            'access_token': result.get('access_token', ''),
            'refresh_token': result.get('refresh_token', refresh_token),
            'expires_in': result.get('expires_in', 1800),
        }

    def fetch_transactions(self, access_token: str, realm_id: str = None, days_back: int = 365) -> List[Dict]:
        since = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%dT00:00:00')
        url = f'{XERO_API}/Invoices?where=Date>=DateTime({since[:10].replace("-",",")})'
        req = urllib.request.Request(url, headers={
            'Authorization': f'Bearer {access_token}',
            'Xero-tenant-id': realm_id or '',
            'Accept': 'application/json',
        })
        try:
            with urllib.request.urlopen(req) as r:
                data = json.loads(r.read())
        except Exception as e:
            logger.error(f'Xero fetch error: {e}')
            return []
        rows = []
        for inv in data.get('Invoices', []):
            rows.append({
                'date': inv.get('Date', '')[:10],
                'amount': inv.get('Total', 0),
                'customer_id': inv.get('Contact', {}).get('ContactID', ''),
                'status': inv.get('Status', '').lower(),
                'description': inv.get('Reference', ''),
                'invoice_id': inv.get('InvoiceNumber', ''),
                'discount': inv.get('TotalDiscount', 0),
            })
        return rows
