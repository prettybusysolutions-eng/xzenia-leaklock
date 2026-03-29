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


def init_consequence_tables():
    """Create System 6 consequence-engine tables if they don't exist."""
    pool = get_pool()
    conn = None
    try:
        conn = pool.getconn()
        cur = conn.cursor()
        cur.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS saas_consequence_cases (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                domain TEXT NOT NULL,
                source_system TEXT NOT NULL,
                source_event_id TEXT NOT NULL,
                scan_id TEXT,
                customer_ref TEXT,
                anomaly_type TEXT NOT NULL,
                evidence JSONB NOT NULL DEFAULT '{}'::jsonb,
                is_synthetic BOOLEAN NOT NULL DEFAULT FALSE,
                status TEXT NOT NULL DEFAULT 'detected',
                detected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                UNIQUE(domain, source_system, source_event_id)
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS saas_consequence_actions (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                case_id UUID NOT NULL REFERENCES saas_consequence_cases(id) ON DELETE CASCADE,
                recommendation TEXT NOT NULL,
                causal_hypothesis TEXT,
                requires_approval BOOLEAN NOT NULL DEFAULT TRUE,
                approval_status TEXT NOT NULL DEFAULT 'pending',
                approved_by TEXT,
                decision_notes TEXT,
                executed_at TIMESTAMPTZ,
                execution_status TEXT NOT NULL DEFAULT 'pending',
                execution_notes TEXT,
                outcome_type TEXT,
                outcome_value NUMERIC(12, 2),
                outcome_currency TEXT DEFAULT 'USD',
                outcome_notes TEXT,
                measured_at TIMESTAMPTZ,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_consequence_cases_domain_detected ON saas_consequence_cases(domain, detected_at DESC)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_consequence_cases_synthetic ON saas_consequence_cases(is_synthetic)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_consequence_actions_case ON saas_consequence_actions(case_id)")
        conn.commit()
        print('[DB] consequence tables ready')
    except Exception as e:
        if conn:
            conn.rollback()
        print(f'[WARN] Could not init consequence tables: {e}')
    finally:
        if conn:
            pool.putconn(conn)


def create_consequence_case(domain, source_system, source_event_id, anomaly_type, evidence, scan_id=None, customer_ref=None, is_synthetic=False):
    """Create or update a System 6 consequence case and return its id."""
    pool = get_pool()
    conn = None
    try:
        conn = pool.getconn()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                INSERT INTO saas_consequence_cases (
                    domain, source_system, source_event_id, scan_id,
                    customer_ref, anomaly_type, evidence, is_synthetic
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, %s)
                ON CONFLICT (domain, source_system, source_event_id)
                DO UPDATE SET
                    scan_id = COALESCE(EXCLUDED.scan_id, saas_consequence_cases.scan_id),
                    customer_ref = COALESCE(EXCLUDED.customer_ref, saas_consequence_cases.customer_ref),
                    anomaly_type = EXCLUDED.anomaly_type,
                    evidence = EXCLUDED.evidence,
                    is_synthetic = EXCLUDED.is_synthetic,
                    status = 'detected'
                RETURNING id::text
                """,
                (
                    domain,
                    source_system,
                    source_event_id,
                    scan_id,
                    customer_ref,
                    anomaly_type,
                    psycopg2.extras.Json(evidence or {}),
                    is_synthetic,
                ),
            )
            row = cur.fetchone()
            conn.commit()
            return row['id'] if row else None
    finally:
        if conn:
            pool.putconn(conn)


def add_consequence_action(case_id, recommendation, causal_hypothesis=None, requires_approval=True):
    """Record a recommended action for a consequence case and return its id."""
    pool = get_pool()
    conn = None
    try:
        conn = pool.getconn()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                INSERT INTO saas_consequence_actions (
                    case_id, recommendation, causal_hypothesis, requires_approval
                )
                VALUES (%s, %s, %s, %s)
                RETURNING id::text
                """,
                (case_id, recommendation, causal_hypothesis, requires_approval),
            )
            row = cur.fetchone()
            conn.commit()
            return row['id'] if row else None
    finally:
        if conn:
            pool.putconn(conn)


def record_action_decision(action_id, approval_status, approved_by=None, decision_notes=None):
    """Record approval or rejection for a consequence action."""
    pool = get_pool()
    conn = None
    try:
        conn = pool.getconn()
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE saas_consequence_actions
                SET approval_status = %s,
                    approved_by = %s,
                    decision_notes = %s
                WHERE id = %s
                """,
                (approval_status, approved_by, decision_notes, action_id),
            )
            conn.commit()
    finally:
        if conn:
            pool.putconn(conn)


def record_action_execution(action_id, execution_status, execution_notes=None):
    """Record execution status for a consequence action."""
    pool = get_pool()
    conn = None
    try:
        conn = pool.getconn()
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE saas_consequence_actions
                SET execution_status = %s,
                    execution_notes = %s,
                    executed_at = CASE WHEN %s IN ('executed', 'failed') THEN NOW() ELSE executed_at END
                WHERE id = %s
                """,
                (execution_status, execution_notes, execution_status, action_id),
            )
            conn.commit()
    finally:
        if conn:
            pool.putconn(conn)


def record_action_outcome(action_id, outcome_type, outcome_value=None, outcome_notes=None, outcome_currency='USD'):
    """Record measured outcome for a consequence action."""
    pool = get_pool()
    conn = None
    try:
        conn = pool.getconn()
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE saas_consequence_actions
                SET outcome_type = %s,
                    outcome_value = %s,
                    outcome_currency = %s,
                    outcome_notes = %s,
                    measured_at = NOW()
                WHERE id = %s
                """,
                (outcome_type, outcome_value, outcome_currency, outcome_notes, action_id),
            )
            conn.commit()
    finally:
        if conn:
            pool.putconn(conn)


def get_proof_metrics(domain='revenue_recovery'):
    """Return proof metrics for System 6 excluding synthetic/demo cases.

    Truth boundary:
    - only non-synthetic cases count as proof
    - demo/sample/test-derived rows are excluded by design
    """
    pool = get_pool()
    conn = None
    try:
        conn = pool.getconn()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT
                    COUNT(*)::int AS real_cases,
                    COUNT(*) FILTER (WHERE c.status = 'detected')::int AS detected_cases,
                    COUNT(a.id)::int AS recommended_actions,
                    COUNT(a.id) FILTER (WHERE a.approval_status = 'approved')::int AS approved_actions,
                    COUNT(a.id) FILTER (WHERE a.execution_status = 'executed')::int AS executed_actions,
                    COALESCE(SUM(a.outcome_value) FILTER (WHERE a.outcome_type IN ('recovered_revenue', 'retained_revenue', 'avoided_loss')), 0)::numeric(12,2) AS realized_value,
                    COUNT(a.id) FILTER (WHERE a.outcome_type IS NOT NULL)::int AS measured_outcomes
                FROM saas_consequence_cases c
                LEFT JOIN saas_consequence_actions a ON a.case_id = c.id
                WHERE c.domain = %s AND c.is_synthetic = FALSE
                """,
                (domain,),
            )
            row = cur.fetchone()
            return dict(row) if row else {}
    finally:
        if conn:
            pool.putconn(conn)


def quarantine_synthetic_cases(scan_ids=None, source_kind_markers=None):
    """Mark known demo/sample-derived consequence cases as synthetic.

    Safe to run when there are no matching rows.
    Returns the number of updated rows.
    """
    pool = get_pool()
    conn = None
    updated = 0
    try:
        conn = pool.getconn()
        with conn.cursor() as cur:
            where_clauses = ["is_synthetic = FALSE"]
            params = []

            if scan_ids:
                where_clauses.append("scan_id = ANY(%s)")
                params.append(list(scan_ids))

            if source_kind_markers:
                marker_clauses = []
                for marker in source_kind_markers:
                    marker_clauses.append("COALESCE(evidence->>'source_kind','') ILIKE %s")
                    params.append(f'%{marker}%')
                if marker_clauses:
                    where_clauses.append('(' + ' OR '.join(marker_clauses) + ')')

            if len(where_clauses) == 1:
                return 0

            cur.execute(
                f"""
                UPDATE saas_consequence_cases
                SET is_synthetic = TRUE,
                    status = CASE WHEN status = 'detected' THEN 'quarantined_synthetic' ELSE status END
                WHERE {' AND '.join(where_clauses)}
                """,
                params,
            )
            updated = cur.rowcount or 0
            conn.commit()
            return updated
    finally:
        if conn:
            pool.putconn(conn)


def get_recent_consequence_cases(domain='revenue_recovery', limit=10):
    """Return recent consequence cases with basic action counts for operator reporting."""
    pool = get_pool()
    conn = None
    try:
        conn = pool.getconn()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT
                    c.id::text AS case_id,
                    c.scan_id,
                    c.source_system,
                    c.source_event_id,
                    c.anomaly_type,
                    c.is_synthetic,
                    c.status,
                    c.detected_at,
                    COALESCE(c.evidence->'estimated_impact'->>'amount', '0') AS estimated_impact_amount,
                    COUNT(a.id)::int AS action_count,
                    COUNT(a.id) FILTER (WHERE a.approval_status = 'pending')::int AS pending_actions,
                    COUNT(a.id) FILTER (WHERE a.approval_status = 'approved')::int AS approved_actions,
                    COUNT(a.id) FILTER (WHERE a.execution_status = 'executed')::int AS executed_actions
                FROM saas_consequence_cases c
                LEFT JOIN saas_consequence_actions a ON a.case_id = c.id
                WHERE c.domain = %s
                GROUP BY c.id
                ORDER BY c.detected_at DESC
                LIMIT %s
                """,
                (domain, limit),
            )
            return [dict(row) for row in cur.fetchall()]
    finally:
        if conn:
            pool.putconn(conn)


def get_proof_report(domain='revenue_recovery'):
    """Return an operator-facing proof report distinguishing real vs synthetic cases."""
    pool = get_pool()
    conn = None
    try:
        conn = pool.getconn()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT
                    COUNT(*) FILTER (WHERE is_synthetic = FALSE)::int AS real_cases,
                    COUNT(*) FILTER (WHERE is_synthetic = TRUE)::int AS synthetic_cases,
                    COUNT(*)::int AS total_cases,
                    COUNT(*) FILTER (WHERE is_synthetic = FALSE AND status = 'detected')::int AS real_detected_cases,
                    COUNT(*) FILTER (WHERE is_synthetic = TRUE AND status = 'detected')::int AS synthetic_detected_cases
                FROM saas_consequence_cases
                WHERE domain = %s
                """,
                (domain,),
            )
            case_counts = dict(cur.fetchone() or {})

            cur.execute(
                """
                SELECT
                    COUNT(a.id) FILTER (WHERE c.is_synthetic = FALSE)::int AS real_actions,
                    COUNT(a.id) FILTER (WHERE c.is_synthetic = TRUE)::int AS synthetic_actions,
                    COUNT(a.id) FILTER (WHERE c.is_synthetic = FALSE AND a.approval_status = 'approved')::int AS real_approved_actions,
                    COUNT(a.id) FILTER (WHERE c.is_synthetic = TRUE AND a.approval_status = 'approved')::int AS synthetic_approved_actions,
                    COUNT(a.id) FILTER (WHERE c.is_synthetic = FALSE AND a.execution_status = 'executed')::int AS real_executed_actions,
                    COUNT(a.id) FILTER (WHERE c.is_synthetic = TRUE AND a.execution_status = 'executed')::int AS synthetic_executed_actions,
                    COALESCE(SUM(a.outcome_value) FILTER (
                        WHERE c.is_synthetic = FALSE
                        AND a.outcome_type IN ('recovered_revenue', 'retained_revenue', 'avoided_loss')
                    ), 0)::numeric(12,2) AS realized_value_real_only,
                    COALESCE(SUM(a.outcome_value) FILTER (
                        WHERE c.is_synthetic = TRUE
                        AND a.outcome_type IN ('recovered_revenue', 'retained_revenue', 'avoided_loss')
                    ), 0)::numeric(12,2) AS realized_value_synthetic_excluded
                FROM saas_consequence_cases c
                LEFT JOIN saas_consequence_actions a ON a.case_id = c.id
                WHERE c.domain = %s
                """,
                (domain,),
            )
            action_counts = dict(cur.fetchone() or {})

            return {
                'domain': domain,
                'proof_boundary': {
                    'counts_as_proof': 'non_synthetic_cases_only',
                    'excluded_from_proof': 'demo_sample_seed_test_cases',
                },
                'cases': case_counts,
                'actions': action_counts,
                'proof_metrics': get_proof_metrics(domain),
                'recent_cases': get_recent_consequence_cases(domain, limit=10),
            }
    finally:
        if conn:
            pool.putconn(conn)
