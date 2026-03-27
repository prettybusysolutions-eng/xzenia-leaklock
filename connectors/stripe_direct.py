"""Stripe Direct API connector — works without Connect OAuth.

Uses the platform's own STRIPE_SECRET_KEY to pull charges, invoices,
and payment intents. No STRIPE_CLIENT_ID required.

When Connect is activated this connector becomes the internal-account
scanner; the OAuth connector handles sub-accounts.
"""
import os
import json
import urllib.request
import urllib.parse
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

STRIPE_API = 'https://api.stripe.com/v1'


def _get(path: str, secret_key: str, params: Dict = None) -> Dict:
    url = STRIPE_API + path
    if params:
        url += '?' + urllib.parse.urlencode(params)
    req = urllib.request.Request(url)
    import base64
    creds = base64.b64encode(f'{secret_key}:'.encode()).decode()
    req.add_header('Authorization', f'Basic {creds}')
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read())


def fetch_charges(secret_key: str, days_back: int = 365, limit: int = 100) -> List[Dict]:
    since = int((datetime.utcnow() - timedelta(days=days_back)).timestamp())
    rows = []
    params = {'limit': limit, 'created[gte]': since}
    while True:
        data = _get('/charges', secret_key, params)
        for ch in data.get('data', []):
            rows.append({
                'date': datetime.utcfromtimestamp(ch.get('created', 0)).strftime('%Y-%m-%d'),
                'amount': ch.get('amount', 0) / 100,
                'customer_id': ch.get('customer') or '',
                'status': ch.get('status', ''),
                'description': ch.get('description') or '',
                'invoice_id': ch.get('invoice') or '',
                'refund': ch.get('amount_refunded', 0) / 100,
                'payment_method': ch.get('payment_method_details', {}).get('type', ''),
            })
        if not data.get('has_more'):
            break
        params['starting_after'] = data['data'][-1]['id']
    return rows


def fetch_invoices(secret_key: str, days_back: int = 365, limit: int = 100) -> List[Dict]:
    since = int((datetime.utcnow() - timedelta(days=days_back)).timestamp())
    rows = []
    params = {'limit': limit, 'created[gte]': since}
    while True:
        data = _get('/invoices', secret_key, params)
        for inv in data.get('data', []):
            rows.append({
                'date': datetime.utcfromtimestamp(inv.get('created', 0)).strftime('%Y-%m-%d'),
                'amount': inv.get('amount_paid', 0) / 100,
                'customer_id': inv.get('customer') or '',
                'status': inv.get('status', ''),
                'description': (inv.get('description') or inv.get('number') or ''),
                'invoice_id': inv.get('id', ''),
                'refund': 0,
                'payment_method': '',
            })
        if not data.get('has_more'):
            break
        params['starting_after'] = data['data'][-1]['id']
    return rows


def fetch_all(secret_key: str, days_back: int = 365) -> List[Dict]:
    """Pull charges + invoices, deduplicated by invoice_id."""
    charges = fetch_charges(secret_key, days_back)
    invoices = fetch_invoices(secret_key, days_back)

    # De-dup: charges that map to an invoice are already in invoices list
    invoice_ids_from_charges = {r['invoice_id'] for r in charges if r['invoice_id']}
    deduped_invoices = [r for r in invoices if r['invoice_id'] not in invoice_ids_from_charges]

    return charges + deduped_invoices


def build_leak_report(rows: List[Dict]) -> Dict:
    """Run basic leak detection on raw rows."""
    total = sum(r['amount'] for r in rows)
    failed = [r for r in rows if r['status'] == 'failed']
    refunded = [r for r in rows if r.get('refund', 0) > 0]
    duplicates = []

    seen = {}
    for r in rows:
        key = (r['customer_id'], r['amount'], r['date'])
        if key in seen:
            duplicates.append(r)
        else:
            seen[key] = r

    leak_amount = sum(r['amount'] for r in failed) + sum(r.get('refund', 0) for r in refunded)

    return {
        'total_revenue': round(total, 2),
        'transactions': len(rows),
        'failed_payments': len(failed),
        'refunds': len(refunded),
        'duplicate_flags': len(duplicates),
        'leak_amount': round(leak_amount, 2),
        'leak_pct': round((leak_amount / total * 100) if total else 0, 2),
        'rows': rows,
    }
