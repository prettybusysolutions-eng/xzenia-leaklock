"""Direct Stripe scan route — no Connect OAuth required.

Pulls live charges + invoices from the platform's own Stripe account
using STRIPE_SECRET_KEY, runs leak detection, and returns a scan result.

This activates LeakLock's core value prop immediately, independently of
Connect ToS completion.
"""
import logging
import os
from flask import Blueprint, redirect, jsonify, request
from connectors.stripe_direct import fetch_all, build_leak_report
from services.cache import cache_set, cache_get
from csv_scanner import save_scan_to_db
from config import DB_CONFIG

logger = logging.getLogger(__name__)
stripe_scan_bp = Blueprint('stripe_scan', __name__, url_prefix='/scan')


@stripe_scan_bp.route('/stripe-direct', methods=['GET'])
def stripe_direct_scan():
    """Run a live Stripe leak scan using platform credentials."""
    sk = os.environ.get('STRIPE_SECRET_KEY', '')
    if not sk:
        return jsonify({'error': 'STRIPE_SECRET_KEY not configured'}), 503

    days_back = int(request.args.get('days', 365))

    try:
        rows = fetch_all(sk, days_back=days_back)
    except Exception as e:
        logger.error(f'Stripe direct fetch failed: {e}')
        return jsonify({'error': str(e)}), 500

    if not rows:
        return jsonify({'error': 'No transactions found', 'transactions': 0}), 200

    report = build_leak_report(rows)

    # Convert to LeakLock canonical scan format
    import uuid
    scan_id = str(uuid.uuid4())

    leaks = []
    if report['failed_payments']:
        failed_rows = [r for r in rows if r['status'] == 'failed']
        leaks.append({
            'pattern_name': 'Failed Payments',
            'description': f"{report['failed_payments']} payment(s) failed and were never recovered.",
            'amount_estimate': sum(r['amount'] for r in failed_rows),
            'affected_rows': report['failed_payments'],
            'severity': 'high',
        })
    if report['refunds']:
        refund_rows = [r for r in rows if r.get('refund', 0) > 0]
        leaks.append({
            'pattern_name': 'Unreviewed Refunds',
            'description': f"{report['refunds']} refund(s) totalling ${sum(r.get('refund',0) for r in refund_rows):,.2f} detected.",
            'amount_estimate': sum(r.get('refund', 0) for r in refund_rows),
            'affected_rows': report['refunds'],
            'severity': 'medium',
        })
    if report['duplicate_flags']:
        leaks.append({
            'pattern_name': 'Duplicate Charge Flags',
            'description': f"{report['duplicate_flags']} transaction(s) share customer + amount + date — potential duplicates.",
            'amount_estimate': 0,
            'affected_rows': report['duplicate_flags'],
            'severity': 'low',
        })

    scan = {
        'scan_id': scan_id,
        'source': 'stripe_direct',
        'account_name': 'Pretty Busy Cleaning (Stripe)',
        'rows_parsed': report['transactions'],
        'total_revenue': report['total_revenue'],
        'total_leakage': report['leak_amount'],
        'patterns_triggered': len(leaks),
        'leaks': leaks,
        'column_mapping': {},
    }

    try:
        cache_set(scan_id, scan)
    except Exception as e:
        logger.warning(f'Cache set failed: {e}')

    try:
        save_scan_to_db(scan, DB_CONFIG)
    except Exception as e:
        logger.warning(f'DB save failed: {e}')

    return redirect(f'/results/{scan_id}')


@stripe_scan_bp.route('/stripe-direct/json', methods=['GET'])
def stripe_direct_json():
    """Return raw JSON report without redirect."""
    sk = os.environ.get('STRIPE_SECRET_KEY', '')
    if not sk:
        return jsonify({'error': 'STRIPE_SECRET_KEY not configured'}), 503

    days_back = int(request.args.get('days', 365))

    try:
        rows = fetch_all(sk, days_back=days_back)
        report = build_leak_report(rows)
        return jsonify(report)
    except Exception as e:
        logger.error(f'Stripe direct JSON scan failed: {e}')
        return jsonify({'error': str(e)}), 500
