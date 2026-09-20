"""Transactional payment notifications. SMTP delivery is at-least-once."""
from models.db import get_pool


def init_outbox():
    pool = get_pool()
    conn = pool.getconn()
    try:
        with conn.cursor() as cur:
            cur.execute('''CREATE TABLE IF NOT EXISTS payment_notification_outbox (
                stripe_session_id TEXT PRIMARY KEY,
                recipient TEXT NOT NULL,
                scan_id TEXT NOT NULL,
                payment_type TEXT NOT NULL,
                amount_cents INTEGER NOT NULL,
                attempts INTEGER NOT NULL DEFAULT 0,
                available_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                sent_at TIMESTAMPTZ,
                last_error TEXT
            )''')
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        pool.putconn(conn)


def enqueue(cursor, session_id, recipient, scan_id, payment_type, amount_cents):
    cursor.execute('''INSERT INTO payment_notification_outbox
        (stripe_session_id, recipient, scan_id, payment_type, amount_cents)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (stripe_session_id) DO NOTHING''',
        (session_id, recipient, scan_id or '', payment_type, amount_cents))


def deliver_one(send=None):
    """Lock one due row across workers; retain failed deliveries for retry.

    A crash after SMTP acceptance but before commit can resend. SMTP provides
    no exactly-once guarantee; a stable Message-ID helps correlate deliveries.
    """
    if send is None:
        from routes.webhooks import _send_payment_confirmation_email
        send = _send_payment_confirmation_email
    pool = get_pool()
    conn = pool.getconn()
    try:
        with conn.cursor() as cur:
            cur.execute('''SELECT stripe_session_id, recipient, scan_id, payment_type, amount_cents
                FROM payment_notification_outbox
                WHERE sent_at IS NULL AND attempts < 8 AND available_at <= NOW()
                ORDER BY available_at FOR UPDATE SKIP LOCKED LIMIT 1''')
            row = cur.fetchone()
            if row is None:
                conn.rollback()
                return 'idle'
            session_id, recipient, scan_id, payment_type, amount = row
            try:
                sent = send(recipient, scan_id, payment_type, amount, notification_id=session_id)
            except Exception:
                sent = False
            if sent:
                cur.execute('''UPDATE payment_notification_outbox
                    SET sent_at=NOW(), attempts=attempts+1, last_error=NULL
                    WHERE stripe_session_id=%s''', (session_id,))
            else:
                cur.execute('''UPDATE payment_notification_outbox
                    SET attempts=attempts+1, last_error='SMTP delivery failed or unconfigured',
                        available_at=NOW() + INTERVAL '1 minute' * POWER(2, attempts)
                    WHERE stripe_session_id=%s''', (session_id,))
        conn.commit()
        return 'sent' if sent else 'retry'
    except Exception:
        conn.rollback()
        raise
    finally:
        pool.putconn(conn)


def main():
    import argparse
    import time
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--once', action='store_true')
    args = parser.parse_args()
    init_outbox()
    while True:
        state = deliver_one()
        print(f'payment-notification: {state}', flush=True)
        if args.once:
            return
        if state != 'sent':
            time.sleep(5)


if __name__ == '__main__':
    main()
