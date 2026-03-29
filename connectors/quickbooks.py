"""QuickBooks Online OAuth connector."""
import os
import json
import urllib.parse
import urllib.request
import logging
from datetime import datetime, timedelta
from typing import Dict, List
from .base import BaseConnector

logger = logging.getLogger(__name__)

QB_AUTH_URL = 'https://appcenter.intuit.com/connect/oauth2'
QB_TOKEN_URL = 'https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer'
QB_API_BASE = 'https://quickbooks.api.intuit.com/v3/company'
QB_SANDBOX_BASE = 'https://sandbox-quickbooks.api.intuit.com/v3/company'
QB_SCOPES = 'com.intuit.quickbooks.accounting'


class QuickBooksConnector(BaseConnector):
    platform = 'quickbooks'

    def __init__(self):
        super().__init__()
        self.client_id = os.environ.get('QB_CLIENT_ID', '')
        self.client_secret = os.environ.get('QB_CLIENT_SECRET', '')
        self.sandbox = os.environ.get('QB_SANDBOX', 'true').lower() == 'true'
        self.api_base = QB_SANDBOX_BASE if self.sandbox else QB_API_BASE

    def get_auth_url(self, state: str) -> str:
        params = {
            'client_id': self.client_id,
            'response_type': 'code',
            'scope': QB_SCOPES,
            'redirect_uri': self.redirect_uri,
            'state': state,
        }
        return QB_AUTH_URL + '?' + urllib.parse.urlencode(params)

    def exchange_code(self, code: str, state: str) -> Dict:
        import base64
        credentials = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode()).decode()
        data = urllib.parse.urlencode({
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': self.redirect_uri,
        }).encode()
        req = urllib.request.Request(QB_TOKEN_URL, data=data, headers={
            'Authorization': f'Basic {credentials}',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json',
        })
        with urllib.request.urlopen(req) as r:
            result = json.loads(r.read())
        return {
            'access_token': result.get('access_token', ''),
            'refresh_token': result.get('refresh_token', ''),
            'expires_in': result.get('expires_in', 3600),
            'realm_id': state.split('|')[1] if '|' in state else '',
            'account_name': 'QuickBooks Company',
        }

    def refresh_access_token(self, refresh_token: str) -> Dict:
        import base64
        credentials = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode()).decode()
        data = urllib.parse.urlencode({
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token,
        }).encode()
        req = urllib.request.Request(QB_TOKEN_URL, data=data, headers={
            'Authorization': f'Basic {credentials}',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json',
        })
        with urllib.request.urlopen(req) as r:
            result = json.loads(r.read())
        return {
            'access_token': result.get('access_token', ''),
            'refresh_token': result.get('refresh_token', refresh_token),
            'expires_in': result.get('expires_in', 3600),
        }

    def fetch_transactions(self, access_token: str, realm_id: str = None, days_back: int = 365) -> List[Dict]:
        since = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
        query = urllib.parse.quote(f"SELECT * FROM Invoice WHERE TxnDate >= '{since}' MAXRESULTS 1000")
        url = f"{self.api_base}/{realm_id}/query?query={query}&minorversion=65"
        req = urllib.request.Request(url, headers={
            'Authorization': f'Bearer {access_token}',
            'Accept': 'application/json',
        })
        try:
            with urllib.request.urlopen(req) as r:
                data = json.loads(r.read())
        except Exception as e:
            logger.error(f'QB fetch error: {e}')
            return []

        rows = []
        invoices = data.get('QueryResponse', {}).get('Invoice', [])
        for inv in invoices:
            rows.append({
                'date': inv.get('TxnDate', ''),
                'amount': inv.get('TotalAmt', 0),
                'customer_id': inv.get('CustomerRef', {}).get('value', ''),
                'status': 'paid' if inv.get('Balance', 1) == 0 else 'unpaid',
                'description': inv.get('CustomerMemo', {}).get('value', ''),
                'invoice_id': inv.get('Id', ''),
                'discount': inv.get('GlobalTaxCalculation', ''),
            })
        return rows
