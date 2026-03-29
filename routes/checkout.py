"""Checkout routes for LeakLock."""
from flask import Blueprint, redirect, request
import stripe

from config import STRIPE_SECRET_KEY, LEAKLOCK_DOMAIN
from templates import page_payment_success
from services.stripe_client import create_checkout_session
from services.cache import cache_get

checkout_bp = Blueprint('checkout', __name__, url_prefix='/checkout')

stripe.api_key = STRIPE_SECRET_KEY


@checkout_bp.route('/recovery/<scan_id>')
def checkout_recovery(scan_id):
    """Create Stripe checkout for recovery fee."""
    if not stripe.api_key:
        return '<h1>Payment not configured yet.</h1>', 503
    
    # Get scan data
    scan = None
    try:
        scan = cache_get(f"scan_{scan_id}")
    except Exception:
        pass
    
    if not scan:
        # Try DB
        from models.db import get_scan_leaks_from_db
        try:
            db_leaks = get_scan_leaks_from_db(scan_id)
            if db_leaks:
                total_leakage = sum(l.get('amount_estimate', 0) for l in db_leaks)
                scan = {
                    'scan_id': scan_id,
                    'total_leakage': total_leakage,
                }
        except Exception:
            pass
    
    if not scan:
        return '<h1>Scan not found</h1>', 404
    
    total_leakage = scan.get('total_leakage', 0)
    if total_leakage <= 0:
        return '<h1>No leakage detected</h1>', 400
    
    tier = request.args.get('tier', 'self')
    if tier == 'done':
        fee_pct = 0.20
        fee_min = 199
        product_name = 'LeakLock Done-With-You Recovery'
    else:
        fee_pct = 0.10
        fee_min = 99
        product_name = 'LeakLock Self-Serve Recovery'
    
    fee = max(fee_min, int(total_leakage * fee_pct))
    
    try:
        session = create_checkout_session(
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': product_name,
                        'description': f'{tier.capitalize()} recovery fee. Scan #{scan_id[:8]}',
                    },
                    'unit_amount': fee * 100,
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=f"{LEAKLOCK_DOMAIN}/payment/success?scan_id={scan_id}&session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{LEAKLOCK_DOMAIN}/results/{scan_id}",
            metadata={'scan_id': scan_id, 'type': 'recovery_fee', 'tier': tier}
        )
        return redirect(session.url, code=303)
    except Exception as e:
        print(f'[ERROR] Stripe checkout failed: {e}')
        return '<h1>Payment error. Please contact hello@leaklock.io</h1>', 500


@checkout_bp.route('/self-serve')
def checkout_self_serve():
    """Self-serve recovery checkout (10% fee) — proxy to checkout_recovery with tier=self."""
    scan_id = request.args.get('scan_id', '').strip()
    if not scan_id:
        return '<h1>No scan specified</h1>', 400
    return redirect(f'/checkout/recovery/{scan_id}?tier=self', code=302)


@checkout_bp.route('/done-with-you')
def checkout_done_with_you():
    """Done-with-you recovery checkout (20% fee) — proxy to checkout_recovery with tier=done."""
    scan_id = request.args.get('scan_id', '').strip()
    if not scan_id:
        return '<h1>No scan specified</h1>', 400
    return redirect(f'/checkout/recovery/{scan_id}?tier=done', code=302)


@checkout_bp.route('/guardian')
def checkout_guardian():
    """Create Stripe checkout for Guardian subscription."""
    if not stripe.api_key:
        return '<h1>Payment not configured yet.</h1>', 503
    
    try:
        session = create_checkout_session(
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': 'LeakLock Guardian',
                        'description': 'Continuous revenue leak monitoring. Cancel anytime.',
                    },
                    'unit_amount': 34900,
                    'recurring': {'interval': 'month'},
                },
                'quantity': 1,
            }],
            mode='subscription',
            success_url=f"{LEAKLOCK_DOMAIN}/payment/success?type=guardian&session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{LEAKLOCK_DOMAIN}/pricing",
            metadata={'type': 'guardian_subscription'}
        )
        return redirect(session.url, code=303)
    except stripe.error.StripeError as e:
        return f'<h1>Payment error: {e.user_message or "Please try again."}</h1>', 500
    except Exception as e:
        import traceback
        print(f'[ERROR] Checkout error: {traceback.format_exc()}')
        return '<h1>Something went wrong. Please try again or contact support.</h1>', 500


@checkout_bp.route('/starter')
def checkout_starter():
    """Create Stripe checkout for Starter subscription."""
    if not stripe.api_key:
        return '<h1>Payment not configured yet.</h1>', 503
    
    try:
        session = create_checkout_session(
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': 'LeakLock Starter',
                        'description': '1 scan/mo, email report, 7 patterns',
                    },
                    'unit_amount': 9900,
                    'recurring': {'interval': 'month'},
                },
                'quantity': 1,
            }],
            mode='subscription',
            success_url=f"{LEAKLOCK_DOMAIN}/payment/success?type=starter&session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{LEAKLOCK_DOMAIN}/pricing",
        )
        return redirect(session.url, code=303)
    except stripe.error.StripeError as e:
        return f'<h1>Payment error: {e.user_message or "Please try again."}</h1>', 500
    except Exception as e:
        import traceback
        print(f'[ERROR] Checkout error: {traceback.format_exc()}')
        return '<h1>Something went wrong. Please try again or contact support.</h1>', 500


@checkout_bp.route('/pro')
def checkout_pro():
    """Create Stripe checkout for Pro subscription."""
    if not stripe.api_key:
        return '<h1>Payment not configured yet.</h1>', 503
    
    try:
        session = create_checkout_session(
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': 'LeakLock Pro',
                        'description': '5 scans/mo, all 15 patterns, PDF reports',
                    },
                    'unit_amount': 24900,
                    'recurring': {'interval': 'month'},
                },
                'quantity': 1,
            }],
            mode='subscription',
            success_url=f"{LEAKLOCK_DOMAIN}/payment/success?type=pro&session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{LEAKLOCK_DOMAIN}/pricing",
        )
        return redirect(session.url, code=303)
    except stripe.error.StripeError as e:
        return f'<h1>Payment error: {e.user_message or "Please try again."}</h1>', 500
    except Exception as e:
        import traceback
        print(f'[ERROR] Checkout error: {traceback.format_exc()}')
        return '<h1>Something went wrong. Please try again or contact support.</h1>', 500
