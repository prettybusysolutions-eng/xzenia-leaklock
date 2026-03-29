"""Stripe Direct API connector — works without Connect OAuth.

Uses the platform's own STRIPE_SECRET_KEY to pull charges and run
accurate leak detection. No STRIPE_CLIENT_ID required.

When Connect is activated this connector becomes the internal-account
scanner; the OAuth connector handles sub-accounts.
"""
import os
import json
import urllib.request
import urllib.parse
import base64
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List

logger = logging.getLogger(__name__)

STRIPE_API = 'https://api.stripe.com/v1'


def _get(path: str, secret_key: str, params: Dict = None) -> Dict:
    url = STRIPE_API + path
    if params:
        url += '?' + urllib.parse.urlencode(params)
    req = urllib.request.Request(url)
    creds = base64.b64encode(f'{secret_key}:'.encode()).decode()
    req.add_header('Authorization', f'Basic {creds}')
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read())


def get_account_name(secret_key: str) -> str:
    """Pull the account's business name from Stripe."""
    try:
        d = _get('/account', secret_key)
        return d.get('business_profile', {}).get('name') or d.get('display_name') or 'Stripe Account'
    except Exception:
        return 'Stripe Account'


def fetch_charges(secret_key: str, days_back: int = 365, limit: int = 100) -> List[Dict]:
    """Fetch all charges — the single source of truth. No invoices needed."""
    since = int((datetime.now(timezone.utc) - timedelta(days=days_back)).timestamp())
    rows = []
    params = {'limit': limit, 'created[gte]': since}
    while True:
        data = _get('/charges', secret_key, params)
        for ch in data.get('data', []):
            rows.append({
                'id': ch.get('id', ''),
                'date': datetime.fromtimestamp(ch.get('created', 0), tz=timezone.utc).strftime('%Y-%m-%d'),
                'timestamp': ch.get('created', 0),
                'amount': ch.get('amount', 0) / 100,
                'amount_refunded': ch.get('amount_refunded', 0) / 100,
                'customer_id': ch.get('customer') or '',
                'status': ch.get('status', ''),
                'description': ch.get('description') or '',
                'invoice_id': ch.get('invoice') or '',
                'refund': ch.get('amount_refunded', 0) / 100,
                'payment_method': ch.get('payment_method_details', {}).get('type', '') if ch.get('payment_method_details') else '',
                'failure_code': ch.get('failure_code') or '',
                'failure_message': ch.get('failure_message') or '',
            })
        if not data.get('has_more'):
            break
        params['starting_after'] = data['data'][-1]['id']
    return rows


def build_leak_report(rows: List[Dict]) -> Dict:
    """
    Accurate leak detection on charge rows.

    Leak sources:
      1. Failed charges that were never recovered (no matching succeeded charge
         for same customer+amount within 7 days)
      2. Full refunds (amount_refunded == original amount)

    Duplicate flags: charges with identical (customer_id, amount) within a
    24-hour rolling window — flagged for review, NOT counted as leak amount.
    """
    if not rows:
        return {
            'total_revenue': 0, 'transactions': 0, 'failed_payments': 0,
            'recovered_payments': 0, 'refunds': 0, 'duplicate_flags': 0,
            'leak_amount': 0, 'leak_pct': 0, 'rows': [],
        }

    succeeded = [r for r in rows if r['status'] == 'succeeded']
    failed = [r for r in rows if r['status'] == 'failed']
    total_revenue = sum(r['amount'] for r in succeeded)

    # ---- Failed payment analysis ----
    # A failed charge is "recovered" if the same customer paid the same amount
    # within 7 days of the failure.
    recovered_ids = set()
    unrecovered_failed = []
    for f in failed:
        window_end = f['timestamp'] + 7 * 86400
        recovered = any(
            s['customer_id'] == f['customer_id']
            and abs(s['amount'] - f['amount']) < 0.01
            and f['timestamp'] <= s['timestamp'] <= window_end
            for s in succeeded
        )
        if recovered:
            recovered_ids.add(f['id'])
        else:
            unrecovered_failed.append(f)

    # ---- Refund analysis ----
    # Only count full refunds (100% of charge amount refunded)
    full_refunds = [r for r in succeeded if r['amount_refunded'] >= r['amount'] * 0.99 and r['amount'] > 0]

    # ---- Duplicate flags (not counted as leaks) ----
    duplicate_ids = set()
    for i, r1 in enumerate(succeeded):
        for r2 in succeeded[i+1:]:
            if (r1['customer_id'] and r1['customer_id'] == r2['customer_id']
                    and abs(r1['amount'] - r2['amount']) < 0.01
                    and abs(r1['timestamp'] - r2['timestamp']) < 86400):
                duplicate_ids.add(r1['id'])
                duplicate_ids.add(r2['id'])

    # ---- Leak totals ----
    failed_leak = sum(r['amount'] for r in unrecovered_failed)
    refund_leak = sum(r['amount_refunded'] for r in full_refunds)
    leak_amount = failed_leak + refund_leak

    return {
        'total_revenue': round(total_revenue, 2),
        'transactions': len(rows),
        'succeeded': len(succeeded),
        'failed_payments': len(unrecovered_failed),
        'recovered_payments': len(recovered_ids),
        'refunds': len(full_refunds),
        'duplicate_flags': len(duplicate_ids),
        'leak_amount': round(leak_amount, 2),
        'leak_pct': round((leak_amount / total_revenue * 100) if total_revenue else 0, 2),
        'failed_detail': unrecovered_failed,
        'refund_detail': full_refunds,
        'rows': rows,
    }
