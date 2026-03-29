"""Stripe integration service."""
import stripe
from config import STRIPE_SECRET_KEY, LEAKLOCK_DOMAIN, STRIPE_WEBHOOK_ID

stripe.api_key = STRIPE_SECRET_KEY


def create_checkout_session(line_items, mode='payment', success_url=None, cancel_url=None, metadata=None):
    """Create a Stripe checkout session."""
    kwargs = {
        'payment_method_types': ['card'],
        'line_items': line_items,
        'mode': mode,
        'success_url': success_url or f"{LEAKLOCK_DOMAIN}/payment/success",
        'cancel_url': cancel_url or f"{LEAKLOCK_DOMAIN}/pricing",
    }
    if metadata:
        kwargs['metadata'] = metadata
    
    return stripe.checkout.Session.create(**kwargs)


def update_webhook_url(new_url):
    """Update Stripe webhook URL."""
    if not STRIPE_WEBHOOK_ID:
        return None
    return stripe.WebhookEndpoint.modify(
        STRIPE_WEBHOOK_ID,
        url=f"{new_url}/webhook/stripe"
    )
