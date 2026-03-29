#!/usr/bin/env python3
"""
Stripe Connector - OAuth and Webhook Handler for LeakLock SaaS
Connects customer Stripe accounts via OAuth and listens for billing events.
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional
import psycopg2
from psycopg2.extras import RealDictCursor

# Setup logging
LOG_DIR = os.path.dirname(os.path.abspath(__file__)) + "/logs"
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f"{LOG_DIR}/stripe_connector.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Database connection
DB_CONFIG = {
    'dbname': 'nexus',
    'user': 'marcuscoarchitect',
    'host': 'localhost'
}

# Stripe configuration (would use env vars in production)
STRIPE_CLIENT_ID = os.environ.get('STRIPE_CLIENT_ID', 'ca_test_your_client_id')
STRIPE_CLIENT_SECRET = os.environ.get('STRIPE_CLIENT_SECRET', 'sk_test_your_secret')
REDIRECT_URI = os.environ.get('STRIPE_REDIRECT_URI', 'http://localhost:5000/oauth/callback')


def get_db_connection():
    """Get database connection."""
    return psycopg2.connect(**DB_CONFIG)


def store_stripe_account(stripe_account_id: str, email: str = None, plan_tier: str = 'starter') -> str:
    """Store connected Stripe account in database."""
    import secrets
    secret_token = secrets.token_urlsafe(32)
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO saas_customers (stripe_account_id, stripe_email, plan_tier, secret_token, status)
                VALUES (%s, %s, %s, %s, 'active')
                ON CONFLICT (stripe_account_id) DO UPDATE SET
                    stripe_email = EXCLUDED.stripe_email,
                    connected_at = NOW(),
                    status = 'active'
                RETURNING id::text
            """, (stripe_account_id, email, plan_tier, secret_token))
            customer_id = cur.fetchone()[0]
            conn.commit()
            logger.info(f"Stored Stripe account {stripe_account_id}, customer_id: {customer_id}")
            return customer_id
    finally:
        conn.close()


def handle_webhook(payload: dict, signature: str = None) -> Dict:
    """
    Handle incoming Stripe webhook events.
    Processes: charges, subscriptions, invoices, payments.
    """
    event_type = payload.get('type', 'unknown')
    data = payload.get('data', {}).get('object', {})
    
    logger.info(f"Processing webhook event: {event_type}")
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Extract relevant information based on event type
            if event_type in ['charge.failed', 'charge.succeeded', 'charge.refunded']:
                customer_id = data.get('customer')
                amount = data.get('amount', 0)
                currency = data.get('currency', 'usd')
                status = data.get('status')
                description = data.get('description', '')
                
                # Insert into billing_events (existing table)
                cur.execute("""
                    INSERT INTO billing_events (source, event_type, amount, status, customer_id, description, metadata)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, ('stripe', event_type, amount, status, customer_id, description, json.dumps(data)))
                
            elif event_type == 'invoice.payment_failed':
                customer_id = data.get('customer')
                amount = data.get('amount_due', 0)
                invoice_id = data.get('id')
                
                cur.execute("""
                    INSERT INTO billing_events (source, event_type, amount, status, customer_id, description, metadata)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, ('stripe', event_type, amount, 'failed', customer_id, f"Invoice {invoice_id} failed", json.dumps(data)))
                
            elif event_type == 'customer.subscription.created':
                customer_id = data.get('customer')
                subscription_id = data.get('id')
                plan_id = data.get('plan', {}).get('id')
                
                # Update customer with subscription info
                cur.execute("""
                    UPDATE saas_customers 
                    SET status = 'subscribed'
                    WHERE stripe_account_id = %s
                """, (customer_id,))
                
            elif event_type == 'customer.subscription.updated':
                customer_id = data.get('customer')
                status = data.get('status')
                
                cur.execute("""
                    UPDATE saas_customers 
                    SET status = %s
                    WHERE stripe_account_id = %s
                """, (status, customer_id))
                
            elif event_type == 'customer.subscription.deleted':
                customer_id = data.get('customer')
                
                cur.execute("""
                    UPDATE saas_customers 
                    SET status = 'cancelled'
                    WHERE stripe_account_id = %s
                """, (customer_id,))
                
            conn.commit()
            logger.info(f"Webhook processed: {event_type}")
            return {'status': 'success', 'event_type': event_type}
            
    except Exception as e:
        logger.error(f"Webhook processing error: {e}")
        conn.rollback()
        return {'status': 'error', 'message': str(e)}
    finally:
        conn.close()


def get_connected_accounts() -> List[Dict]:
    """Get all connected Stripe accounts."""
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT id::text, stripe_account_id, stripe_email, plan_tier, status, connected_at
                FROM saas_customers WHERE status IN ('active', 'subscribed')
            """)
            return cur.fetchall()
    finally:
        conn.close()


def get_customer_by_token(secret_token: str) -> Optional[Dict]:
    """Get customer by secret token (for dashboard auth)."""
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT id::text, stripe_account_id, stripe_email, plan_tier, status, secret_token
                FROM saas_customers WHERE secret_token = %s
            """, (secret_token,))
            result = cur.fetchone()
            return dict(result) if result else None
    finally:
        conn.close()


# OAuth URL generator for Stripe Connect
def get_oauth_url(state: str = None) -> str:
    """Generate Stripe Connect OAuth URL."""
    import secrets
    if not state:
        state = secrets.token_urlsafe(16)
    return f"https://connect.stripe.com/oauth/authorize?response_type=code&client_id={STRIPE_CLIENT_ID}&scope=read_write&redirect_uri={REDIRECT_URI}&state={state}"


# Demo function to simulate Stripe connection
def demo_connect_stripe(email: str = "demo@company.com", plan: str = "starter") -> Dict:
    """Demo function to connect a test Stripe account."""
    import uuid
    demo_account_id = f"acct_{uuid.uuid4().hex[:16]}"
    customer_id = store_stripe_account(demo_account_id, email, plan)
    logger.info(f"Demo connected: {demo_account_id}")
    return {'customer_id': customer_id, 'stripe_account_id': demo_account_id}


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "demo-connect":
        result = demo_connect_stripe()
        print(f"Demo connection created: {result}")
    elif len(sys.argv) > 1 and sys.argv[1] == "list-accounts":
        accounts = get_connected_accounts()
        print(f"Connected accounts: {json.dumps(accounts, default=str, indent=2)}")
    else:
        print("Stripe Connector for LeakLock")
        print("Usage:")
        print("  python stripe_connector.py demo-connect   - Create demo account")
        print("  python stripe_connector.py list-accounts - List connected accounts")