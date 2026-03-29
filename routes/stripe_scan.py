"""Direct Stripe scan route — no Connect OAuth required.

Pulls live charges from the platform's own Stripe account using
STRIPE_SECRET_KEY, runs accurate leak detection, returns scan result.

Endpoints:
  GET /scan/stripe-direct          → loading page → redirect to results
  GET /scan/stripe-direct/run      → run scan, redirect to /results/{id}
  GET /scan/stripe-direct/json     → raw JSON report
"""
import logging
import os
import uuid
from flask import Blueprint, redirect, jsonify, request, Response

logger = logging.getLogger(__name__)
stripe_scan_bp = Blueprint('stripe_scan', __name__, url_prefix='/scan')


def _run_scan(days_back: int = 365):
    """Internal: run scan, return (scan_dict, error_str)."""
    from connectors.stripe_direct import fetch_charges, build_leak_report, get_account_name
    from services.cache import cache_set
    from csv_scanner import save_scan_to_db
    from config import DB_CONFIG

    sk = os.environ.get('STRIPE_SECRET_KEY', '')
    if not sk:
        return None, 'STRIPE_SECRET_KEY not configured'

    try:
        account_name = get_account_name(sk)
        rows = fetch_charges(sk, days_back=days_back)
    except Exception as e:
        logger.error('Stripe direct fetch failed: %s', e)
        return None, str(e)

    if not rows:
        return None, 'no_transactions'

    report = build_leak_report(rows)
    scan_id = str(uuid.uuid4())

    leaks = []

    # Failed / unrecovered payments
    if report['failed_payments']:
        failed_rows = report.get('failed_detail', [])
        codes = list({r['failure_code'] for r in failed_rows if r['failure_code']})
        leaks.append({
            'pattern_name': 'Failed Payments',
            'description': (
                f"{report['failed_payments']} payment(s) failed and were never recovered. "
                f"Failure codes: {', '.join(codes) if codes else 'unknown'}."
            ),
            'how_to_fix': (
                'Set up Stripe Smart Retries or contact customers directly to update '
                'payment methods. Consider enabling payment dunning emails.'
            ),
            'amount_estimate': round(sum(r['amount'] for r in failed_rows), 2),
            'affected_rows': report['failed_payments'],
            'severity': 'high',
        })

    # Full refunds
    if report['refunds']:
        refund_rows = report.get('refund_detail', [])
        leaks.append({
            'pattern_name': 'Full Refunds',
            'description': (
                f"{report['refunds']} charge(s) were fully refunded totalling "
                f"${sum(r['amount_refunded'] for r in refund_rows):,.2f}."
            ),
            'how_to_fix': (
                'Review refund patterns — frequent full refunds may indicate '
                'service delivery issues, unclear pricing, or billing errors.'
            ),
            'amount_estimate': round(sum(r['amount_refunded'] for r in refund_rows), 2),
            'affected_rows': report['refunds'],
            'severity': 'medium',
        })

    # Duplicate charge flags
    if report['duplicate_flags']:
        leaks.append({
            'pattern_name': 'Possible Duplicate Charges',
            'description': (
                f"{report['duplicate_flags']} succeeded charge(s) share the same customer "
                f"and amount within a 24-hour window. These may be duplicates."
            ),
            'how_to_fix': (
                'Review these charges manually in your Stripe dashboard. '
                'If duplicates, issue refunds and enable idempotency keys in your integration.'
            ),
            'amount_estimate': 0,
            'affected_rows': report['duplicate_flags'],
            'severity': 'low',
        })

    total_leakage = sum(l['amount_estimate'] for l in leaks)

    scan = {
        'scan_id': scan_id,
        'source': 'stripe_direct',
        'account_name': account_name,
        'rows_parsed': report['transactions'],
        'total_revenue': report['total_revenue'],
        'total_leakage': round(total_leakage, 2),
        'patterns_triggered': len(leaks),
        'leaks': leaks,
        'column_mapping': {},
        'stripe_report': {
            'succeeded': report['succeeded'],
            'failed_payments': report['failed_payments'],
            'recovered_payments': report['recovered_payments'],
            'refunds': report['refunds'],
            'duplicate_flags': report['duplicate_flags'],
            'leak_pct': report['leak_pct'],
        },
    }

    try:
        cache_set(scan_id, scan)
    except Exception as e:
        logger.warning('Cache set failed: %s', e)

    try:
        save_scan_to_db(scan, DB_CONFIG)
    except Exception as e:
        logger.warning('DB save failed: %s', e)

    return scan, None


@stripe_scan_bp.route('/stripe-direct', methods=['GET'])
def stripe_direct_loading():
    """Show a loading page that immediately JS-redirects to the actual scan."""
    days = request.args.get('days', '365')
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Scanning your Stripe account... — LeakLock</title>
<style>
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'Inter',-apple-system,sans-serif;background:#060d1b;color:#f1f5f9;
  display:flex;align-items:center;justify-content:center;min-height:100vh}}
.wrap{{text-align:center;padding:40px}}
.spinner{{width:56px;height:56px;border:4px solid rgba(56,189,248,0.2);
  border-top-color:#38bdf8;border-radius:50%;animation:spin 0.9s linear infinite;
  margin:0 auto 32px}}
@keyframes spin{{to{{transform:rotate(360deg)}}}}
h2{{font-size:24px;font-weight:700;margin-bottom:12px;letter-spacing:-0.5px}}
p{{color:#94a3b8;font-size:15px}}
.dots span{{animation:blink 1.4s infinite;opacity:0}}
.dots span:nth-child(2){{animation-delay:0.2s}}
.dots span:nth-child(3){{animation-delay:0.4s}}
@keyframes blink{{0%,80%,100%{{opacity:0}}40%{{opacity:1}}}}
</style>
</head>
<body>
<div class="wrap">
  <div class="spinner"></div>
  <h2>Scanning your Stripe account<span class="dots"><span>.</span><span>.</span><span>.</span></span></h2>
  <p>Pulling transactions and running leak analysis.<br>This takes just a few seconds.</p>
</div>
<script>
  setTimeout(function(){{
    window.location.href = '/scan/stripe-direct/run?days={days}';
  }}, 800);
</script>
</body>
</html>"""
    return Response(html, content_type='text/html')


@stripe_scan_bp.route('/stripe-direct/run', methods=['GET'])
def stripe_direct_run():
    """Execute scan and redirect to results page."""
    days_back = int(request.args.get('days', 365))
    scan, err = _run_scan(days_back)

    if err == 'no_transactions':
        return '<h1>No transactions found in the last year.</h1><p><a href="/upload">Upload a file instead</a></p>', 200

    if err:
        return f'<h1>Scan failed</h1><p>{err}</p><p><a href="/upload">Try uploading a file</a></p>', 500

    return redirect(f"/results/{scan['scan_id']}")


@stripe_scan_bp.route('/stripe-direct/json', methods=['GET'])
def stripe_direct_json():
    """Return raw JSON report."""
    days_back = int(request.args.get('days', 365))
    scan, err = _run_scan(days_back)

    if err:
        return jsonify({'error': err}), (503 if 'not configured' in err else 500)

    return jsonify(scan)
