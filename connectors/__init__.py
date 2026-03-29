"""OAuth connectors for LeakLock billing platform integrations."""
from .base import BaseConnector, normalize_to_scan_rows
from .quickbooks import QuickBooksConnector
from .stripe_connect import StripeConnector
from .square import SquareConnector
from .xero import XeroConnector
from .freshbooks import FreshBooksConnector

CONNECTORS = {
    'quickbooks': QuickBooksConnector,
    'stripe': StripeConnector,
    'square': SquareConnector,
    'xero': XeroConnector,
    'freshbooks': FreshBooksConnector,
}

PLATFORM_META = {
    'quickbooks': {'name': 'QuickBooks Online', 'icon': '📒', 'color': '#2CA01C', 'description': 'Connect your QuickBooks account'},
    'stripe': {'name': 'Stripe', 'icon': '💳', 'color': '#635BFF', 'description': 'Connect your Stripe account'},
    'square': {'name': 'Square', 'icon': '⬛', 'color': '#3E4348', 'description': 'Connect your Square account'},
    'xero': {'name': 'Xero', 'icon': '🔷', 'color': '#13B5EA', 'description': 'Connect your Xero account'},
    'freshbooks': {'name': 'FreshBooks', 'icon': '📗', 'color': '#1DB65D', 'description': 'Connect your FreshBooks account'},
}
