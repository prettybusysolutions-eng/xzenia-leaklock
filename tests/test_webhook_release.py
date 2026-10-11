import hashlib
import hmac
import json
import time

import pytest
from app import create_app
import routes.webhooks as hooks


@pytest.mark.parametrize('fail,expected', [(False, 200), (True, 503)])
def test_signed_webhook_with_csrf_enabled(monkeypatch, fail, expected):
    secret = 'whsec_local_fixture'
    monkeypatch.setattr(hooks, 'STRIPE_WEBHOOK_SECRET', secret)
    seen = []
    def handle(event):
        seen.append(event['id'])
        if fail:
            raise RuntimeError('simulated database outage')
    monkeypatch.setattr(hooks, '_handle_stripe_event', handle)
    monkeypatch.setattr(hooks, '_record_webhook_processed', lambda *a: None)
    monkeypatch.setattr(hooks, '_enqueue_dlq', lambda *a: None)
    app = create_app()
    app.config.update(TESTING=True, WTF_CSRF_ENABLED=True)
    body = json.dumps({'id': 'evt_local', 'object': 'event', 'type': 'checkout.session.completed',
                       'data': {'object': {}}})
    timestamp = str(int(time.time()))
    digest = hmac.new(secret.encode(), f'{timestamp}.{body}'.encode(), hashlib.sha256).hexdigest()
    client = app.test_client()
    response = client.post('/webhook/stripe', data=body,
                           headers={'Stripe-Signature': f't={timestamp},v1={digest}'})
    assert response.status_code == expected
    assert seen == ['evt_local']
    assert client.post('/webhook/stripe', data=body,
                       headers={'Stripe-Signature': f't={timestamp},v1=invalid'}).status_code == 400
    assert client.post('/webhook/stripe/retry-dlq').status_code == 400


def test_unpaid_checkout_does_not_record_payment(monkeypatch):
    def forbidden():
        pytest.fail('unpaid checkout accessed payment database')
    monkeypatch.setattr(hooks, 'get_pool', forbidden)
    hooks._handle_stripe_event({'type': 'checkout.session.completed', 'data': {'object': {
        'id': 'cs_unpaid', 'payment_status': 'unpaid', 'customer_details': None}}})
