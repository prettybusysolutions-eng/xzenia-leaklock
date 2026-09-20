"""Real PostgreSQL checks; each test owns an isolated temporary schema."""
import os
import uuid
from concurrent.futures import ThreadPoolExecutor

import psycopg2
from psycopg2.pool import ThreadedConnectionPool
import pytest
import models.db as database
import routes.webhooks as hooks


@pytest.fixture
def pg(monkeypatch):
    url = os.environ.get('RELEASE_TEST_POSTGRES_URL')
    if not url:
        pytest.skip('RELEASE_TEST_POSTGRES_URL is required for PostgreSQL evidence')
    schema = 'release_' + uuid.uuid4().hex
    admin = psycopg2.connect(url)
    admin.autocommit = True
    with admin.cursor() as cur:
        cur.execute(f'CREATE SCHEMA {schema}')
    pool = ThreadedConnectionPool(1, 10, url, options=f'-csearch_path={schema}')
    monkeypatch.setattr(database, 'get_pool', lambda: pool)
    monkeypatch.setattr(hooks, 'get_pool', lambda: pool)
    monkeypatch.setattr('routes.api.get_pool', lambda: pool)
    monkeypatch.setattr('services.payment_notifications.get_pool', lambda: pool)
    database.init_payments_table()
    database.init_webhook_dlq_table()
    from services.payment_notifications import init_outbox
    init_outbox()
    yield pool
    pool.closeall()
    with admin.cursor() as cur:
        cur.execute(f'DROP SCHEMA {schema} CASCADE')
    admin.close()


def event():
    return {'id': 'evt_release', 'type': 'checkout.session.completed', 'data': {'object': {
        'id': 'cs_release', 'payment_status': 'paid', 'amount_total': 1000,
        'customer_details': None, 'metadata': {'scan_id': str(uuid.UUID(int=1))}}}}


def test_notification_is_atomic_deduplicated_and_retryable(pg):
    from services.payment_notifications import deliver_one
    payment = event()
    payment['data']['object']['customer_details'] = {'email': 'synthetic@example.invalid'}
    with ThreadPoolExecutor(max_workers=4) as executor:
        list(executor.map(lambda _: hooks._handle_stripe_event(payment), range(8)))
    assert deliver_one(send=lambda *a, **k: False) == 'retry'
    assert deliver_one(send=lambda *a, **k: True) == 'idle'
    conn = pg.getconn()
    try:
        with conn.cursor() as cur:
            cur.execute('SELECT COUNT(*), MAX(attempts) FROM payment_notification_outbox')
            assert cur.fetchone() == (1, 1)
            cur.execute('UPDATE payment_notification_outbox SET available_at=NOW()')
        conn.commit()
    finally:
        pg.putconn(conn)
    delivered = []
    def send(*args, **kwargs):
        delivered.append(kwargs['notification_id'])
        return True
    with ThreadPoolExecutor(max_workers=4) as executor:
        states = list(executor.map(lambda _: deliver_one(send=send), range(4)))
    assert states.count('sent') == 1
    assert delivered == ['cs_release']
    hooks._handle_stripe_event(payment)
    assert deliver_one(send=send) == 'idle'


def test_outbox_failure_rolls_back_payment(pg):
    payment = event()
    payment['data']['object']['customer_details'] = {'email': 'synthetic@example.invalid'}
    conn = pg.getconn()
    try:
        with conn.cursor() as cur:
            cur.execute('DROP TABLE payment_notification_outbox')
        conn.commit()
    finally:
        pg.putconn(conn)
    with pytest.raises(psycopg2.Error):
        hooks._handle_stripe_event(payment)
    conn = pg.getconn()
    try:
        with conn.cursor() as cur:
            cur.execute('SELECT COUNT(*) FROM saas_payments')
            assert cur.fetchone() == (0,)
    finally:
        conn.rollback()
        pg.putconn(conn)


def test_concurrent_duplicate_payment_and_schema_rerun(pg):
    with ThreadPoolExecutor(max_workers=4) as executor:
        list(executor.map(lambda _: hooks._handle_stripe_event(event()), range(8)))
    database.init_payments_table()
    conn = pg.getconn()
    try:
        with conn.cursor() as cur:
            cur.execute('SELECT COUNT(*), SUM(amount_cents) FROM saas_payments')
            assert cur.fetchone() == (1, 1000)
    finally:
        conn.rollback()
        pg.putconn(conn)


def test_failure_rollback_dlq_resolution_and_reuse(pg):
    invalid = event()
    invalid['data']['object']['metadata']['scan_id'] = 'invalid-uuid'
    with pytest.raises(psycopg2.Error):
        hooks._handle_stripe_event(invalid)
    hooks._enqueue_dlq('evt_release', 'checkout.session.completed', event(), 'fixture failure')
    hooks._handle_stripe_event(event())
    hooks._record_webhook_processed('evt_release', 'checkout.session.completed')
    conn = pg.getconn()
    try:
        with conn.cursor() as cur:
            cur.execute('SELECT status FROM webhook_dead_letter_queue WHERE stripe_event_id=%s', ('evt_release',))
            assert cur.fetchone() == ('resolved',)
            cur.execute('SELECT COUNT(*) FROM saas_payments')
            assert cur.fetchone() == (1,)
    finally:
        conn.rollback()
        pg.putconn(conn)


def test_missing_payment_schema_fails_readiness(pg):
    from app import create_app
    client = create_app().test_client()
    assert client.get('/health').status_code == 200
    conn = pg.getconn()
    try:
        with conn.cursor() as cur:
            cur.execute('DROP TABLE saas_payments')
        conn.commit()
    finally:
        pg.putconn(conn)
    assert client.get('/health').status_code == 503
    database.init_payments_table()
    assert client.get('/health').status_code == 200
