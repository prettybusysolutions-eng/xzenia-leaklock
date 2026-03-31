"""Webhook routes for LeakLock."""
from flask import Blueprint, request
import stripe
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from config import STRIPE_WEBHOOK_SECRET, LEAKLOCK_DOMAIN
from models.db import get_pool

webhooks_bp = Blueprint('webhooks', __name__, url_prefix='/webhook')


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
        ptype = metadata.get('type', 'recovery_fee')
        customer_email = session_data.get('customer_details', {}).get('email', '') or \
                         session_data.get('customer_email', '')
        amount_cents = session_data.get('amount_total', 0)

        print(f'[STRIPE] Payment completed: type={ptype}, scan_id={scan_id}, email={customer_email}, amount={amount_cents}')

        # Log payment to DB
        try:
            pool = get_pool()
            conn = pool.getconn()
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
            pool.putconn(conn)
            print(f'[STRIPE] Payment recorded: session={session_data.get("id")}')
        except Exception as e:
            print(f'[WARN] Failed to log payment to DB: {e}')

        # Send confirmation email
        if customer_email and '@' in customer_email:
            _send_payment_confirmation_email(customer_email, scan_id or '', ptype, amount_cents)

    return 'ok', 200
