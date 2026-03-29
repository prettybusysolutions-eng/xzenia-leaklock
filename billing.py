#!/usr/bin/env python3
"""
Billing Webhook Handler - Processes Stripe subscription events
Handles: subscription.created, subscription.updated, subscription.deleted
Tracks customer plan in saas_customers.
"""

import os
import json
import logging
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs
import hmac
import hashlib
import psycopg2
from psycopg2.extras import RealDictCursor

# Setup logging
LOG_DIR = os.path.dirname(os.path.abspath(__file__)) + "/logs"
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f"{LOG_DIR}/billing.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configuration
DB_CONFIG = {
    'dbname': 'nexus',
    'user': 'marcuscoarchitect',
    'host': 'localhost'
}

STRIPE_WEBHOOK_SECRET = os.environ.get('STRIPE_WEBHOOK_SECRET', 'whsec_test_secret')
PORT = int(os.environ.get('BILLING_PORT', 5001))


def get_db_connection():
    """Get database connection."""
    return psycopg2.connect(**DB_CONFIG)


def verify_webhook_signature(payload: bytes, signature: str) -> bool:
    """Verify Stripe webhook signature."""
    if not STRIPE_WEBHOOK_SECRET or STRIPE_WEBHOOK_SECRET == 'whsec_test_secret':
        logger.warning("Webhook secret not set - skipping signature verification")
        return True
    
    try:
        expected_sig = hmac.new(
            STRIPE_WEBHOOK_SECRET.encode('utf-8'),
            payload,
            hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(f"sha256={expected_sig}", signature)
    except Exception as e:
        logger.error(f"Signature verification error: {e}")
        return False


def handle_subscription_created(event_data: dict) -> dict:
    """Handle subscription.created event."""
    customer_id = event_data.get('customer')
    subscription_id = event_data.get('id')
    status = event_data.get('status')
    plan = event_data.get('plan', {})
    plan_tier = map_plan_from_stripe(plan)
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE saas_customers 
                SET status = 'subscribed', plan_tier = %s
                WHERE stripe_account_id = %s
            """, (plan_tier, customer_id))
            conn.commit()
            logger.info(f"Subscription created: {subscription_id} for {customer_id}, plan: {plan_tier}")
            return {'status': 'success', 'customer_id': customer_id, 'plan': plan_tier}
    except Exception as e:
        logger.error(f"Error handling subscription created: {e}")
        return {'status': 'error', 'message': str(e)}
    finally:
        conn.close()


def handle_subscription_updated(event_data: dict) -> dict:
    """Handle subscription.updated event."""
    customer_id = event_data.get('customer')
    subscription_id = event_data.get('id')
    status = event_data.get('status')
    plan = event_data.get('plan', {})
    plan_tier = map_plan_from_stripe(plan)
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE saas_customers 
                SET status = %s, plan_tier = %s
                WHERE stripe_account_id = %s
            """, (status, plan_tier, customer_id))
            conn.commit()
            logger.info(f"Subscription updated: {subscription_id} for {customer_id}, status: {status}")
            return {'status': 'success', 'customer_id': customer_id, 'status': status}
    except Exception as e:
        logger.error(f"Error handling subscription updated: {e}")
        return {'status': 'error', 'message': str(e)}
    finally:
        conn.close()


def handle_subscription_deleted(event_data: dict) -> dict:
    """Handle subscription.deleted event."""
    customer_id = event_data.get('customer')
    subscription_id = event_data.get('id')
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE saas_customers 
                SET status = 'cancelled'
                WHERE stripe_account_id = %s
            """, (customer_id,))
            conn.commit()
            logger.info(f"Subscription cancelled: {subscription_id} for {customer_id}")
            return {'status': 'success', 'customer_id': customer_id}
    except Exception as e:
        logger.error(f"Error handling subscription deleted: {e}")
        return {'status': 'error', 'message': str(e)}
    finally:
        conn.close()


def map_plan_from_stripe(plan: dict) -> str:
    """Map Stripe plan to internal tier."""
    if not plan:
        return 'starter'
    
    amount = plan.get('amount', 0) or 0
    interval = plan.get('interval', 'month')
    
    if amount >= 50000:  # $500+
        return 'enterprise'
    elif amount >= 25000:  # $250+
        return 'pro'
    else:
        return 'starter'


def process_webhook(payload: bytes, signature: str) -> dict:
    """Process incoming webhook payload."""
    # Verify signature
    if not verify_webhook_signature(payload, signature):
        logger.warning("Invalid webhook signature")
        return {'status': 'error', 'message': 'Invalid signature'}
    
    try:
        event = json.loads(payload)
        event_type = event.get('type')
        event_data = event.get('data', {}).get('object', {})
        
        logger.info(f"Processing webhook: {event_type}")
        
        handlers = {
            'subscription.created': handle_subscription_created,
            'subscription.updated': handle_subscription_updated,
            'subscription.deleted': handle_subscription_deleted
        }
        
        handler = handlers.get(event_type)
        if handler:
            return handler(event_data)
        else:
            logger.info(f"Unhandled event type: {event_type}")
            return {'status': 'skipped', 'event_type': event_type}
            
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in webhook: {e}")
        return {'status': 'error', 'message': 'Invalid JSON'}
    except Exception as e:
        logger.error(f"Webhook processing error: {e}")
        return {'status': 'error', 'message': str(e)}


class WebhookHandler(BaseHTTPRequestHandler):
    """HTTP handler for Stripe webhooks."""
    
    def do_POST(self):
        if self.path != '/webhook':
            self.send_error(404, "Not found")
            return
        
        content_length = int(self.headers.get('Content-Length', 0))
        payload = self.rfile.read(content_length)
        signature = self.headers.get('Stripe-Signature', '')
        
        result = process_webhook(payload, signature)
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(result).encode())
    
    def log_message(self, format, *args):
        logger.info(format % args)


def run_webhook_server():
    """Run the webhook server."""
    server = HTTPServer(('0.0.0.0', PORT), WebhookHandler)
    print(f"🔗 LeakLock Billing Webhook Server running on http://localhost:{PORT}/webhook")
    server.serve_forever()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "serve":
        run_webhook_server()
    else:
        print("LeakLock Billing Webhooks")
        print("Usage: python billing.py serve")
        print("   Runs webhook server on port 5001")