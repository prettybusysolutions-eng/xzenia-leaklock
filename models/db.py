"""Database connection and queries for LeakLock."""
import psycopg2
import psycopg2.pool
import psycopg2.extras
from psycopg2.extras import RealDictCursor
from config import DB_CONFIG

# Connection pool - lazily initialized
_pool = None


def get_pool():
    """Get or create the database connection pool."""
    global _pool
    if _pool is None:
        _pool = psycopg2.pool.SimpleConnectionPool(
            1, 10,
            host=DB_CONFIG['host'],
            dbname=DB_CONFIG['dbname'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password'],
            port=DB_CONFIG['port'],
        )
    return _pool


def get_connection():
    """Get a connection from the pool."""
    return get_pool().getconn()


def return_connection(conn):
    """Return a connection to the pool."""
    get_pool().putconn(conn)


def get_db():
    """Get a raw psycopg2 connection (for legacy code that doesn't use pool)."""
    return psycopg2.connect(
        host=DB_CONFIG['host'],
        dbname=DB_CONFIG['dbname'],
        user=DB_CONFIG['user'],
        password=DB_CONFIG['password'],
        port=DB_CONFIG['port'],
    )


def get_customer_with_token(customer_id, token):
    """Get customer by ID and token."""
    pool = get_pool()
    conn = pool.getconn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT id::text, stripe_account_id, stripe_email, plan_tier,
                       status, connected_at, last_scan_at
                FROM saas_customers WHERE id = %s AND secret_token = %s
            """, (customer_id, token))
            r = cur.fetchone()
            return dict(r) if r else None
    finally:
        pool.putconn(conn)


def get_detected_leaks(customer_id):
    """Get all detected leaks for a customer."""
    pool = get_pool()
    conn = pool.getconn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT id::text, pattern, amount_estimate, confidence,
                       severity, details, status, detected_at
                FROM saas_detected_leaks WHERE customer_id = %s
                ORDER BY detected_at DESC, amount_estimate DESC
            """, (customer_id,))
            return [dict(r) for r in cur.fetchall()]
    finally:
        pool.putconn(conn)


def get_scan_leaks_from_db(scan_id):
    """Retrieve leaks for a given scan_id from DB."""
    pool = get_pool()
    conn = pool.getconn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT pattern, amount_estimate, confidence, severity, details, detected_at
                FROM saas_detected_leaks WHERE scan_id = %s
                ORDER BY amount_estimate DESC
            """, (scan_id,))
            return [dict(r) for r in cur.fetchall()]
    finally:
        pool.putconn(conn)


def capture_email(scan_id, email):
    """Capture email for a scan."""
    pool = get_pool()
    conn = pool.getconn()
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO saas_scan_emails (scan_id, email, captured_at)
            VALUES (%s, %s, NOW())
            ON CONFLICT (scan_id) DO UPDATE SET email = EXCLUDED.email
        """, (scan_id, email))
        conn.commit()
    finally:
        pool.putconn(conn)


def init_payments_table():
    """Create saas_payments table if it doesn't exist."""
    pool = get_pool()
    try:
        conn = pool.getconn()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS saas_payments (
                id SERIAL PRIMARY KEY,
                stripe_session_id TEXT UNIQUE,
                scan_id UUID,
                payment_type TEXT,
                customer_email TEXT,
                amount_cents INTEGER,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        conn.commit()
        pool.putconn(conn)
        print('[DB] saas_payments table ready')
    except Exception as e:
        print(f'[WARN] Could not init saas_payments table: {e}')


def init_scan_emails_table():
    """Create saas_scan_emails table if it doesn't exist."""
    pool = get_pool()
    conn = None
    try:
        conn = pool.getconn()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS saas_scan_emails (
                id SERIAL PRIMARY KEY,
                scan_id TEXT NOT NULL,
                email TEXT NOT NULL,
                captured_at TIMESTAMPTZ DEFAULT NOW(),
                UNIQUE(scan_id)
            )
        """)
        conn.commit()
        print('[DB] saas_scan_emails table ready')
    except Exception as e:
        if conn:
            conn.rollback()
        print(f'[WARN] Could not init saas_scan_emails table: {e}')
    finally:
        if conn:
            pool.putconn(conn)


def init_connections_table():
    """Create saas_connections table if it doesn't exist."""
    pool = get_pool()
    conn = None
    try:
        conn = pool.getconn()
        cur = conn.cursor()
        cur.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS saas_connections (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                platform TEXT NOT NULL,
                user_email TEXT NOT NULL,
                access_token_enc TEXT NOT NULL,
                refresh_token_enc TEXT,
                token_expires_at TIMESTAMPTZ,
                realm_id TEXT,
                account_name TEXT,
                connected_at TIMESTAMPTZ DEFAULT NOW(),
                last_sync_at TIMESTAMPTZ,
                status TEXT DEFAULT 'active',
                UNIQUE(platform, user_email)
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_connections_email ON saas_connections(user_email)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_connections_platform ON saas_connections(platform, status)")
        conn.commit()
        print('[DB] saas_connections table ready')
    except Exception as e:
        if conn:
            conn.rollback()
        print(f'[WARN] Could not init saas_connections table: {e}')
    finally:
        if conn:
            pool.putconn(conn)



def init_scan_cache_table():
    """Create scan_cache table if it doesn't exist."""
    pool = get_pool()
    conn = None
    try:
        conn = pool.getconn()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS scan_cache (
                cache_key TEXT PRIMARY KEY,
                payload JSONB NOT NULL,
                expires_at TIMESTAMPTZ,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_scan_cache_expires_at ON scan_cache(expires_at)")
        conn.commit()
        print('[DB] scan_cache table ready')
    except Exception as e:
        if conn:
            conn.rollback()
        print(f'[WARN] Could not init scan_cache table: {e}')
    finally:
        if conn:
            pool.putconn(conn)
