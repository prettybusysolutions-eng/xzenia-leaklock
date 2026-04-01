"""Webhook routes for LeakLock."""
from flask import Blueprint, request
import stripe
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone

from config import STRIPE_WEBHOOK_SECRET, LEAKLOCK_DOMAIN
from models.db import get_pool

webhooks_bp = Blueprint('webhooks', __name__, url_prefix='/webhook')


def _enqueue_dlq(stripe_event_id: str, event_type: str, payload: dict, error_message: str):
    """Store a failed webhook event in the dead letter queue."""
    try:
        pool = get_pool()
        conn = pool.getconn()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO webhook_dead_letter_queue
                (stripe_event_id, event_type, payload, error_message, status, retry_count, created_at)
            VALUES (%s, %s, %s, %s, 'pending', 0, NOW())
            ON CONFLICT (stripe_event_id) DO UPDATE
                SET error_message = EXCLUDED.error_message,
                    retry_count = webhook_dead_letter_queue.retry_count,
                    last_retry_at = NOW()
        """, (stripe_event_id, event_type, json.dumps(payload), error_message))
        conn.commit()
        pool.putconn(conn)
        print(f'[DLQ] Event {stripe_event_id} queued: {error_message}')
    except Exception as e:
        print(f'[DLQ] Failed to enqueue event {stripe_event_id}: {e}')


def _record_webhook_processed(stripe_event_id: str, event_type: str):
    """Mark a Stripe event as successfully processed (idempotency check)."""
    try:
        pool = get_pool()
        conn = pool.getconn()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO webhook_dead_letter_queue
                (stripe_event_id, event_type, payload, error_message, status, created_at)
            VALUES (%s, %s, '{}'::jsonb, 'PROCESSED', 'resolved', NOW())
            ON CONFLICT (stripe_event_id) DO NOTHING
        """, (stripe_event_id, event_type))
        conn.commit()
        pool.putconn(conn)
    except Exception:
        pass  # Best effort


def _send_payment_confirmation_email(to_email: str, scan_id: str, ptype: str, amount_cents: int):
    """Send a payment confirmation email with results link."""
    import os
    smtp_host = os.environ.get('SMTP_HOST', '')
    smtp_port = int(os.environ.get('SMTP_PORT', '587'))
    smtp_user = os.environ.get('SMTP_USER', '')
    smtp_pass = os.environ.get('SMTP_PASS', '')
    from_email = os.environ.get('SMTP_FROM', 'hello@leaklock.io')
    
    if not smtp_host or not smtp_user or not smtp_pass:
        print(f'[STRIPE] SMTP not configured — skipping email to {to_email}')
        return False
    
    amount_str = f"${amount_cents/100:,.2f}"
    product_names = {
        'recovery_fee': 'LeakLock Recovery Results',
        'self': 'LeakLock Self-Serve Recovery',
        'done': 'LeakLock Done-With-You Recovery',
        'guardian': 'LeakLock Guardian',
        'starter': 'LeakLock Starter',
        'pro': 'LeakLock Pro',
    }
    product_name = product_names.get(ptype, 'LeakLock')
    
    results_url = f"{LEAKLOCK_DOMAIN}/results/{scan_id}"
    msg = MIMEMultipart('alternative')
    msg['Subject'] = f'Payment Confirmed — {product_name}'
    msg['From'] = from_email
    msg['To'] = to_email
    
    text_body = f"""Payment confirmed.

Product: {product_name}
Amount: {amount_str}
Scan ID: {scan_id}

View your results: {results_url}

— The LeakLock Team
"""
    html_body = f"""
<!DOCTYPE html>
<html>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 24px; color: #1a1a2e;">
  <div style="background: linear-gradient(135deg, #0f172a 0%, #1e3a5f 100%); padding: 32px; border-radius: 16px 16px 0 0;">
    <h1 style="color: #ffffff; margin: 0; font-size: 28px; font-weight: 700;">Payment Confirmed ✓</h1>
    <p style="color: #94a3b8; margin: 8px 0 0 0;">LeakLock</p>
  </div>
  <div style="background: #ffffff; padding: 32px; border: 1px solid #e2e8f0; border-top: none; border-radius: 0 0 16px 16px;">
    <table style="width: 100%; border-collapse: collapse; margin-bottom: 24px;">
      <tr><td style="padding: 8px 0; color: #64748b; font-size: 14px;">Product</td><td style="padding: 8px 0; font-weight: 600; text-align: right;">{product_name}</td></tr>
      <tr><td style="padding: 8px 0; color: #64748b; font-size: 14px;">Amount</td><td style="padding: 8px 0; font-weight: 700; font-size: 20px; text-align: right; color: #059669;">{amount_str}</td></tr>
      <tr><td style="padding: 8px 0; color: #64748b; font-size: 14px;">Scan ID</td><td style="padding: 8px 0; font-family: monospace; font-size: 12px; text-align: right;">{scan_id}</td></tr>
    </table>
    <a href="{results_url}" style="display: inline-block; background: #0f172a; color: #ffffff; padding: 14px 28px; border-radius: 8px; text-decoration: none; font-weight: 600; font-size: 16px;">View Your Leak Report →</a>
    <p style="margin-top: 24px; font-size: 13px; color: #94a3b8;">If the button doesn't work, copy this link into your browser:<br>{results_url}</p>
  </div>
</body>
</html>"""
    
    msg.attach(MIMEText(text_body, 'plain'))
    msg.attach(MIMEText(html_body, 'html'))
    
    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.sendmail(from_email, [to_email], msg.as_string())
        print(f'[STRIPE] Confirmation email sent to {to_email}')
        return True
    except Exception as e:
        print(f'[STRIPE] Email send failed to {to_email}: {e}')
        return False


@webhooks_bp.route('/stripe', methods=['POST'])
def stripe_webhook():
    """Handle Stripe webhook events with signature verification and DLQ."""
    from config import STRIPE_SECRET_KEY
    
    stripe.api_key = STRIPE_SECRET_KEY
    
    payload = request.get_data(as_text=True)
    sig_header = request.headers.get('Stripe-Signature', '')

    # STRIPE_WEBHOOK_SECRET is REQUIRED in production
    if not STRIPE_WEBHOOK_SECRET:
        print('[STRIPE] FATAL: STRIPE_WEBHOOK_SECRET not set — rejecting all webhook events')
        return 'Webhook secret not configured', 503

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
    except stripe.error.SignatureVerificationError:
        print('[STRIPE] Invalid signature — rejecting event')
        return 'Invalid signature', 400
    except ValueError as e:
        print(f'[STRIPE] Invalid payload: {e}')
        return 'Invalid payload', 400

    event_type = event.get('type', '')
    stripe_event_id = event.get('id', '')

    # Process with DLQ on failure
    try:
        _handle_stripe_event(event)
        _record_webhook_processed(stripe_event_id, event_type)
        return 'ok', 200
    except Exception as e:
        error_msg = str(e)
        print(f'[STRIPE] Event processing failed: {error_msg}')
        _enqueue_dlq(stripe_event_id, event_type, event, error_msg)
        # Still return 200 to prevent Stripe retry spam for known failure types
        return 'ok', 200


def _handle_stripe_event(event):
    """Process a verified Stripe event. Raises on failure."""
    event_type = event.get('type', '')
    session_data = event['data']['object']
    metadata = session_data.get('metadata', {})
    scan_id = metadata.get('scan_id')
    ptype = metadata.get('type', 'recovery_fee')
    customer_email = session_data.get('customer_details', {}).get('email', '') or \
                     session_data.get('customer_email', '')
    amount_cents = session_data.get('amount_total', 0)

    print(f'[STRIPE] Processing: type={event_type}, scan_id={scan_id}, email={customer_email}')

    if event_type == 'checkout.session.completed':
        # Log payment to DB (ON CONFLICT ensures idempotency)
        pool = get_pool()
        conn = pool.getconn()
        try:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO saas_payments (stripe_session_id, scan_id, payment_type, customer_email, amount_cents, created_at)
                VALUES (%s, %s, %s, %s, %s, NOW())
                ON CONFLICT (stripe_session_id) DO UPDATE
                SET scan_id = COALESCE(EXCLUDED.scan_id, saas_payments.scan_id),
                    payment_type = COALESCE(EXCLUDED.payment_type, saas_payments.payment_type),
                    customer_email = COALESCE(EXCLUDED.customer_email, saas_payments.customer_email),
                    amount_cents = COALESCE(EXCLUDED.amount_cents, saas_payments.amount_cents)
            """, (
                session_data.get('id'),
                scan_id,
                ptype,
                customer_email,
                amount_cents
            ))
            conn.commit()
            print(f'[STRIPE] Payment recorded: session={session_data.get("id")}')
        finally:
            pool.putconn(conn)

        # Send confirmation email
        if customer_email and '@' in customer_email:
            _send_payment_confirmation_email(customer_email, scan_id or '', ptype, amount_cents)


# ── Webhook DLQ Admin Routes ──────────────────────────────────────────────────

@webhooks_bp.route('/stripe/retry-dlq', methods=['POST'])
def retry_dlq():
    """
    Retry pending webhook DLQ events. Admin only.
    Protected by FLASK_ADMIN_KEY env var.
    Usage: POST /webhook/stripe/retry-dlq with header X-Admin-Key
    """
    from config import STRIPE_SECRET_KEY
    import os
    admin_key = os.environ.get('FLASK_ADMIN_KEY', '')
    provided_key = request.headers.get('X-Admin-Key', '')
    
    if not admin_key or provided_key != admin_key:
        return 'Unauthorized', 401
    
    stripe.api_key = STRIPE_SECRET_KEY
    pool = get_pool()
    conn = pool.getconn()
    processed = 0
    failed = 0
    
    try:
        cur = conn.cursor()
        # Get all pending DLQ events
        cur.execute("""
            SELECT id, stripe_event_id, event_type, payload, error_message
            FROM webhook_dead_letter_queue
            WHERE status = 'pending'
            AND retry_count < 5
            ORDER BY created_at ASC
            LIMIT 50
        """)
        rows = cur.fetchall()
        
        for row in rows:
            dlq_id, stripe_event_id, event_type, payload, last_error = row
            try:
                # Re-parse the stored payload and process
                if isinstance(payload, str):
                    payload = json.loads(payload)
                _handle_stripe_event(payload)
                cur.execute("""
                    UPDATE webhook_dead_letter_queue
                    SET status = 'resolved', resolved_at = NOW(), last_retry_at = NOW()
                    WHERE id = %s
                """, (dlq_id,))
                conn.commit()
                processed += 1
            except Exception as e:
                cur.execute("""
                    UPDATE webhook_dead_letter_queue
                    SET retry_count = retry_count + 1,
                        last_retry_at = NOW(),
                        error_message = %s,
                        status = CASE WHEN retry_count + 1 >= 5 THEN 'failed' ELSE 'pending' END
                    WHERE id = %s
                """, (str(e), dlq_id))
                conn.commit()
                failed += 1
        
        pool.putconn(conn)
        return {'processed': processed, 'failed': failed, 'remaining': len(rows) - processed}, 200
    except Exception as e:
        pool.putconn(conn)
        return {'error': str(e)}, 500


@webhooks_bp.route('/stripe/dlq-status', methods=['GET'])
def dlq_status():
    """Get DLQ status. Admin only."""
    import os
    admin_key = os.environ.get('FLASK_ADMIN_KEY', '')
    provided_key = request.headers.get('X-Admin-Key', '')
    if not admin_key or provided_key != admin_key:
        return 'Unauthorized', 401
    
    pool = get_pool()
    conn = pool.getconn()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT status, COUNT(*) as count
            FROM webhook_dead_letter_queue
            GROUP BY status
        """)
        rows = cur.fetchall()
        pool.putconn(conn)
        return {status: count for status, count in rows}, 200
    except Exception as e:
        pool.putconn(conn)
        return {'error': str(e)}, 500
