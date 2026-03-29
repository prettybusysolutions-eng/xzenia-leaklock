"""Routes package - page routes for LeakLock."""
from flask import Blueprint, redirect, request

page_bp = Blueprint('pages', __name__)


def get_scan_by_id(scan_id):
    """Fetch scan from cache or DB."""
    from services.cache import cache_get
    from models.db import get_scan_leaks_from_db
    
    if len(scan_id) < 8:
        return None
    
    try:
        scan = cache_get(f"scan_{scan_id}")
    except Exception:
        scan = None
    
    if not scan:
        try:
            db_leaks = get_scan_leaks_from_db(scan_id)
            if db_leaks:
                import json
                total_leakage = sum(l.get('amount_estimate', 0) for l in db_leaks)
                for l in db_leaks:
                    if l.get('details') and isinstance(l['details'], dict):
                        l['pattern_name'] = l['details'].get('pattern_name', l.get('pattern', '').replace('_', ' ').title())
                        l['description'] = l['details'].get('description', '')
                        l['affected_rows'] = l['details'].get('affected_rows', 0)
                    elif isinstance(l.get('details'), str):
                        try:
                            det = json.loads(l['details'])
                            l['pattern_name'] = det.get('pattern_name', l.get('pattern', '').replace('_', ' ').title())
                            l['description'] = det.get('description', '')
                            l['affected_rows'] = det.get('affected_rows', 0)
                        except:
                            pass
                scan = {
                    'scan_id': scan_id,
                    'rows_parsed': sum(l.get('affected_rows', 1) for l in db_leaks),
                    'total_revenue': total_leakage,
                    'total_leakage': total_leakage,
                    'patterns_triggered': len(db_leaks),
                    'leaks': db_leaks,
                    'column_mapping': {}
                }
        except Exception:
            pass
    
    return scan


@page_bp.route('/')
def landing():
    from templates import page_landing
    return page_landing()


@page_bp.route('/upload', methods=['GET', 'POST'])
def upload():
    from routes.api import handle_upload
    if request.method == 'GET':
        from templates import page_upload
        return page_upload()
    return handle_upload()


@page_bp.route('/results/<scan_id>')
def results(scan_id):
    from templates import page_results
    scan = get_scan_by_id(scan_id)
    if not scan:
        return '<h1>Scan not found. Results may have expired — please <a href="/upload">scan again</a>.</h1>', 404
    return page_results(scan)


@page_bp.route('/pricing')
def pricing():
    from templates import page_pricing
    return page_pricing()


@page_bp.route('/dental')
def dental():
    from templates import page_dental
    return page_dental()


@page_bp.route('/contact')
def contact():
    from templates import page_contact
    return page_contact()


@page_bp.route('/privacy')
def privacy():
    from templates import page_privacy
    return page_privacy()


@page_bp.route('/terms')
def terms():
    from templates import page_terms
    return page_terms()


@page_bp.route('/payment/success')
def payment_success():
    from templates import page_payment_success
    ptype = request.args.get('type', 'recovery')
    scan_id = request.args.get('scan_id', '')
    return page_payment_success(ptype, scan_id)


@page_bp.route('/dashboard/<customer_id>')
def dashboard(customer_id):
    from models.db import get_customer_with_token, get_detected_leaks
    from templates import page_legacy_dashboard, _demo_dashboard
    
    token = request.args.get('token', '')
    try:
        customer = get_customer_with_token(customer_id, token)
        if customer:
            leaks = get_detected_leaks(customer_id)
            return page_legacy_dashboard(customer, leaks)
        else:
            return _demo_dashboard(customer_id)
    except Exception as e:
        return f'<h1>Error</h1><pre>{e}</pre>', 500
