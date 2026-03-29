#!/usr/bin/env python3
"""
Leak Detection Engine - Scans Stripe data for 7 revenue leakage patterns

Patterns:
1. Discount Drift - Gradual increase in discount %
2. Usage Underbilling - Usage-based charges not captured
3. Renewal Erosion - Downgrades/cancellations at renewal
4. Scope Creep - Unpaid features delivered without invoicing
5. Credit Memo Overissuance - Excessive credits issued
6. Failed Payment Neglect - Failed charges never retried
7. Contract Term Amnesia - Legacy pricing from expired contracts
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import psycopg2
from psycopg2.extras import RealDictCursor

# Setup logging
LOG_DIR = os.path.dirname(os.path.abspath(__file__)) + "/logs"
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f"{LOG_DIR}/leak_scanner.log"),
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

# Leakage patterns configuration
LEAKAGE_PATTERNS = {
    'discount_drift': {
        'name': 'Discount Drift',
        'description': 'Gradual increase in discount % given to customers over time',
        'severity': 'medium',
        'confidence_weight': 0.75
    },
    'usage_underbilling': {
        'name': 'Usage Underbilling',
        'description': 'Usage-based charges not captured or undercounted',
        'severity': 'high',
        'confidence_weight': 0.80
    },
    'renewal_erosion': {
        'name': 'Renewal Erosion',
        'description': 'Downgrades and cancellations at renewal time',
        'severity': 'high',
        'confidence_weight': 0.85
    },
    'scope_creep': {
        'name': 'Scope Creep',
        'description': 'Unpaid features/services delivered without invoicing',
        'severity': 'medium',
        'confidence_weight': 0.65
    },
    'credit_memo_overissuance': {
        'name': 'Credit Memo Overissuance',
        'description': 'Excessive credits issued beyond valid reasons',
        'severity': 'medium',
        'confidence_weight': 0.70
    },
    'failed_payment_neglect': {
        'name': 'Failed Payment Neglect',
        'description': 'Failed charges that are never retried or recovered',
        'severity': 'high',
        'confidence_weight': 0.90
    },
    'contract_term_amnesia': {
        'name': 'Contract Term Amnesia',
        'description': 'Legacy pricing/effects from expired contracts still active',
        'severity': 'low',
        'confidence_weight': 0.60
    }
}


def get_db_connection():
    """Get database connection."""
    return psycopg2.connect(**DB_CONFIG)


def get_billing_events_for_customer(customer_id: str, days: int = 90) -> List[Dict]:
    """Get billing events for a specific customer using stripe_account_id."""
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # First get the stripe_account_id from saas_customers
            cur.execute("""
                SELECT stripe_account_id FROM saas_customers WHERE id = %s
            """, (customer_id,))
            result = cur.fetchone()
            if not result:
                return []
            stripe_account_id = result['stripe_account_id']
            
            # Then get billing events for that stripe account
            cur.execute("""
                SELECT * FROM billing_events 
                WHERE customer_id = %s 
                AND created_at > NOW() - INTERVAL '%s days'
                ORDER BY created_at DESC
            """, (stripe_account_id, days))
            return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()


def detect_discount_drift(events: List[Dict]) -> Optional[Dict]:
    """
    Pattern 1: Discount Drift
    Detects if discount percentages have been increasing over time.
    """
    # Look for invoice events with discounts
    discount_events = [e for e in events if 'discount' in e.get('description', '').lower() 
                       or 'invoice' in e.get('event_type', '')]
    
    if len(discount_events) < 3:
        return None
    
    # Calculate discount trend (simplified - would use actual discount data in production)
    # For demo, we'll detect if there's a pattern of decreasing amounts with same description
    amounts = [e['amount'] for e in discount_events[:5] if e.get('amount')]
    if not amounts:
        return None
    
    # If amounts are decreasing while customer count stable (proxy for discounts increasing)
    if len(amounts) >= 3 and amounts[-1] < amounts[0] * 0.9:
        avg_loss = int((amounts[0] - amounts[-1]) * 0.5)
        return {
            'pattern': 'discount_drift',
            'amount_estimate': avg_loss,
            'confidence': 0.72,
            'severity': 'medium',
            'details': {
                'trend': 'decreasing',
                'events_analyzed': len(discount_events),
                'first_amount': amounts[0],
                'last_amount': amounts[-1]
            }
        }
    return None


def detect_usage_underbilling(events: List[Dict]) -> Optional[Dict]:
    """
    Pattern 2: Usage Underbilling
    Detects potential usage charges that weren't captured.
    """
    # Look for usage-related events that might be missing from invoices
    usage_events = [e for e in events if 'usage' in e.get('description', '').lower()]
    
    # Check for metered billing events
    invoice_events = [e for e in events if 'invoice' in e.get('event_type', '')]
    
    if invoice_events:
        # Calculate potential underbilling: invoices vs expected usage
        invoice_total = sum(e.get('amount', 0) for e in invoice_events)
        
        # For demo: if there are usage events but lower invoice amounts than expected
        if usage_events and invoice_total < 50000:  # Threshold for demo
            return {
                'pattern': 'usage_underbilling',
                'amount_estimate': int(invoice_total * 0.15),  # 15% potential underbilling
                'confidence': 0.65,
                'severity': 'high',
                'details': {
                    'usage_events': len(usage_events),
                    'invoice_count': len(invoice_events),
                    'total_invoiced': invoice_total
                }
            }
    return None


def detect_renewal_erosion(events: List[Dict]) -> Optional[Dict]:
    """
    Pattern 3: Renewal Erosion
    Detects downgrades and cancellations at renewal.
    """
    # Look for subscription updates that indicate downgrades/cancellations
    renewal_events = [e for e in events if 'subscription' in e.get('event_type', '')]
    
    cancellations = [e for e in renewal_events if 'cancel' in e.get('description', '').lower() 
                     or 'deleted' in e.get('event_type', '')]
    downgrades = [e for e in renewal_events if 'update' in e.get('event_type', '').lower() 
                  and e.get('amount', 0) > 0]
    
    if cancellations or downgrades:
        total_loss = sum(e.get('amount', 0) for e in cancellations + downgrades)
        return {
            'pattern': 'renewal_erosion',
            'amount_estimate': total_loss,
            'confidence': 0.82,
            'severity': 'high',
            'details': {
                'cancellations': len(cancellations),
                'downgrades': len(downgrades),
                'total_events': len(renewal_events)
            }
        }
    return None


def detect_scope_creep(events: List[Dict]) -> Optional[Dict]:
    """
    Pattern 4: Scope Creep
    Detects unpaid features delivered without invoicing.
    """
    # Look for events where services were delivered but no invoice followed
    # This is tricky - in production would need contract data
    
    # For demo: look for service events without corresponding invoices
    service_events = [e for e in events if any(kw in e.get('description', '').lower() 
                       for kw in ['feature', 'service', 'delivered', 'add-on'])]
    
    invoice_events = [e for e in events if 'invoice' in e.get('event_type', '')]
    
    if service_events and len(invoice_events) < len(service_events):
        # Potential scope creep
        return {
            'pattern': 'scope_creep',
            'amount_estimate': sum(e.get('amount', 0) for e in service_events[:3]) * 2,
            'confidence': 0.55,
            'severity': 'medium',
            'details': {
                'service_events': len(service_events),
                'invoices_found': len(invoice_events),
                'gap': len(service_events) - len(invoice_events)
            }
        }
    return None


def detect_credit_memo_overissuance(events: List[Dict]) -> Optional[Dict]:
    """
    Pattern 5: Credit Memo Overissuance
    Detects excessive credits beyond valid reasons.
    """
    credit_events = [e for e in events if 'credit' in e.get('event_type', '').lower() 
                     or 'refund' in e.get('event_type', '').lower()]
    
    if len(credit_events) > 2:
        total_credits = sum(e.get('amount', 0) for e in credit_events)
        charge_events = [e for e in events if 'charge' in e.get('event_type', '').lower()]
        total_charges = sum(e.get('amount', 0) for e in charge_events)
        
        if total_charges > 0:
            credit_ratio = total_credits / total_charges
            if credit_ratio > 0.10:  # >10% credits is suspicious
                return {
                    'pattern': 'credit_memo_overissuance',
                    'amount_estimate': int(total_credits * 0.5),
                    'confidence': 0.70,
                    'severity': 'medium',
                    'details': {
                        'credit_count': len(credit_events),
                        'total_credits': total_credits,
                        'credit_ratio': round(credit_ratio, 2),
                        'total_charges': total_charges
                    }
                }
    return None


def detect_failed_payment_neglect(events: List[Dict]) -> Optional[Dict]:
    """
    Pattern 6: Failed Payment Neglect
    Detects failed charges that were never retried.
    """
    # Failed status events are ones that weren't recovered - that's the leak!
    failed_events = [e for e in events if e.get('status') == 'failed']
    recovered_events = [e for e in events if e.get('status') == 'recovered']
    
    if len(failed_events) > 0:
        failed_total = sum(e.get('amount', 0) for e in failed_events)
        
        # If there are failed payments that were never recovered, that's a leak!
        if failed_total > 0:
            return {
                'pattern': 'failed_payment_neglect',
                'amount_estimate': int(failed_total),
                'confidence': 0.88,
                'severity': 'high',
                'details': {
                    'failed_count': len(failed_events),
                    'recovered_count': len(recovered_events),
                    'unrecovered_total': failed_total,
                    'recovery_rate': 0.0
                }
            }
    return None


def detect_contract_term_amnesia(events: List[Dict]) -> Optional[Dict]:
    """
    Pattern 7: Contract Term Amnesia
    Detects legacy pricing still active from expired contracts.
    """
    # This would need contract data in production
    # For demo: look for stale pricing patterns
    
    # Check if there are old events with inconsistent pricing
    old_events = [e for e in events if e.get('created_at') and 
                 (datetime.now() - e['created_at'].replace(tzinfo=None)).days > 180]
    
    recent_events = [e for e in events if e.get('created_at') and 
                     (datetime.now() - e['created_at'].replace(tzinfo=None)).days < 30]
    
    if old_events and recent_events:
        old_avg = sum(e.get('amount', 0) for e in old_events) / len(old_events)
        recent_avg = sum(e.get('amount', 0) for e in recent_events) / len(recent_events)
        
        # If pricing hasn't changed much despite time passing, might be stale
        if abs(old_avg - recent_avg) < old_avg * 0.05:
            return {
                'pattern': 'contract_term_amnesia',
                'amount_estimate': int(old_avg * 0.1),
                'confidence': 0.45,
                'severity': 'low',
                'details': {
                    'old_events': len(old_events),
                    'recent_events': len(recent_events),
                    'avg_amount': int(recent_avg)
                }
            }
    return None


def scan_customer(customer_id: str) -> Dict:
    """
    Run all 7 leakage pattern detectors against a customer's billing events.
    """
    logger.info(f"Scanning customer: {customer_id}")
    
    # Get billing events (90 days for starter, 365 for pro/enterprise)
    events = get_billing_events_for_customer(customer_id, days=90)
    
    logger.info(f"Retrieved {len(events)} billing events for customer {customer_id}")
    
    if not events:
        return {
            'customer_id': customer_id,
            'status': 'no_events',
            'leaks_detected': [],
            'total_estimated_loss': 0
        }
    
    detected_leaks = []
    
    # Run all pattern detectors
    detectors = [
        detect_discount_drift,
        detect_usage_underbilling,
        detect_renewal_erosion,
        detect_scope_creep,
        detect_credit_memo_overissuance,
        detect_failed_payment_neglect,
        detect_contract_term_amnesia
    ]
    
    for detector in detectors:
        try:
            result = detector(events)
            if result:
                detected_leaks.append(result)
                logger.info(f"Detected: {result['pattern']} - ${result['amount_estimate']}")
                
                # Store in database
                store_detected_leak(customer_id, result)
        except Exception as e:
            logger.error(f"Error in {detector.__name__}: {e}")
    
    # Calculate total estimated loss
    total_loss = sum(leak['amount_estimate'] for leak in detected_leaks)
    
    # Update last scan time
    update_customer_scan_time(customer_id)
    
    return {
        'customer_id': customer_id,
        'status': 'complete',
        'events_analyzed': len(events),
        'leaks_detected': detected_leaks,
        'total_estimated_loss': total_loss,
        'scan_timestamp': datetime.now().isoformat()
    }


def store_detected_leak(customer_id: str, leak: Dict):
    """Store detected leak in database."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO saas_detected_leaks 
                (customer_id, pattern, amount_estimate, confidence, severity, details, status)
                VALUES (%s, %s, %s, %s, %s, %s, 'detected')
            """, (
                customer_id,
                leak['pattern'],
                leak['amount_estimate'],
                leak['confidence'],
                leak['severity'],
                json.dumps(leak.get('details', {}))
            ))
            conn.commit()
    except Exception as e:
        logger.error(f"Error storing leak: {e}")
    finally:
        conn.close()


def update_customer_scan_time(customer_id: str):
    """Update last scan timestamp for customer."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE saas_customers SET last_scan_at = NOW() WHERE id = %s
            """, (customer_id,))
            conn.commit()
    finally:
        conn.close()


def scan_all_customers() -> Dict:
    """Scan all active customers."""
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT id::text FROM saas_customers WHERE status IN ('active', 'subscribed')
            """)
            customers = cur.fetchall()
    finally:
        conn.close()
    
    results = []
    for customer in customers:
        result = scan_customer(customer['id'])
        results.append(result)
    
    total_loss = sum(r['total_estimated_loss'] for r in results)
    
    return {
        'scan_time': datetime.now().isoformat(),
        'customers_scanned': len(customers),
        'total_estimated_loss': total_loss,
        'results': results
    }


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "scan-all":
        results = scan_all_customers()
        print(json.dumps(results, default=str, indent=2))
    elif len(sys.argv) > 2 and sys.argv[1] == "scan":
        customer_id = sys.argv[2]
        results = scan_customer(customer_id)
        print(json.dumps(results, default=str, indent=2))
    else:
        print("Leak Scanner for LeakLock")
        print("Usage:")
        print("  python leak_scanner.py scan-all        - Scan all customers")
        print("  python leak_scanner.py scan <customer_id> - Scan specific customer")