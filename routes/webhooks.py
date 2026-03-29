"""Webhook routes for LeakLock."""
from flask import Blueprint, request
import stripe
import json

from config import STRIPE_WEBHOOK_SECRET
from models.db import get_pool

webhooks_bp = Blueprint('webhooks', __name__, url_prefix='/webhook')


@webhooks_bp.route('/stripe', methods=['POST'])
def stripe_webhook():
    """Handle Stripe webhook events."""
    from config import STRIPE_SECRET_KEY
    
    stripe.api_key = STRIPE_SECRET_KEY
    
    payload = request.get_data(as_text=True)
    sig_header = request.headers.get('Stripe-Signature', '')

    if STRIPE_WEBHOOK_SECRET:
        try:
            event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
        except stripe.error.SignatureVerificationError:
            return 'Invalid signature', 400
    else:
        try:
            event = json.loads(payload)
        except Exception:
            return 'Invalid payload', 400

    event_type = event.get('type', '')

    if event_type == 'checkout.session.completed':
        session_data = event['data']['object']
        metadata = session_data.get('metadata', {})
        scan_id = metadata.get('scan_id')
        ptype = metadata.get('type')
        customer_email = session_data.get('customer_details', {}).get('email', '')

        print(f'[STRIPE] Payment completed: type={ptype}, scan_id={scan_id}, email={customer_email}')

        # Log to DB
        try:
            pool = get_pool()
            conn = pool.getconn()
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO saas_payments (stripe_session_id, scan_id, payment_type, customer_email, amount_cents, created_at)
                VALUES (%s, %s, %s, %s, %s, NOW())
                ON CONFLICT (stripe_session_id) DO NOTHING
            """, (
                session_data.get('id'),
                scan_id,
                ptype,
                customer_email,
                session_data.get('amount_total', 0)
            ))
            conn.commit()
            pool.putconn(conn)
        except Exception as e:
            print(f'[WARN] Failed to log payment to DB: {e}')

    return 'ok', 200
