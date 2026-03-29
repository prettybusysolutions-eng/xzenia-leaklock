"""Database connection and queries for LeakLock."""
import json
import psycopg2
import psycopg2.pool
import psycopg2.extras
from psycopg2.extras import RealDictCursor
from config import DB_CONFIG

# Connection pool - lazily initialized
_pool = None

VALID_APPROVAL_STATUSES = {'pending', 'approved', 'rejected'}
VALID_EXECUTION_STATUSES = {'pending', 'executed', 'failed'}
VALID_VERIFICATION_STATUSES = {'unverified', 'pending', 'verified', 'disputed'}


def _clean_text(value):
    """Return a stripped string value or empty string."""
    if value is None:
        return ''
    return str(value).strip()


def _normalize_actor_payload(actor=None, actor_id=None, actor_type=None, allow_legacy=True):
    """Normalize actor identity into a structured truth-bearing payload."""
    structured = actor if isinstance(actor, dict) else None
    if structured:
        normalized_actor_id = _clean_text(structured.get('actor_id') or actor_id)
        normalized_actor_type = _clean_text(structured.get('actor_type') or actor_type)
        if not normalized_actor_id or not normalized_actor_type:
            raise ValueError('actor.actor_id and actor.actor_type are required')
        return {
            'actor_id': normalized_actor_id,
            'actor_type': normalized_actor_type,
            'display_name': _clean_text(structured.get('display_name')) or None,
            'auth_subject': _clean_text(structured.get('auth_subject')) or None,
            'auth_provider': _clean_text(structured.get('auth_provider')) or None,
            'legacy': False,
            'raw_actor': None,
        }

    normalized_actor_id = _clean_text(actor_id)
    normalized_actor_type = _clean_text(actor_type)
    if normalized_actor_id and normalized_actor_type:
        return {
            'actor_id': normalized_actor_id,
            'actor_type': normalized_actor_type,
            'display_name': None,
            'auth_subject': None,
            'auth_provider': None,
            'legacy': False,
            'raw_actor': None,
        }

    legacy_actor = _clean_text(actor)
    if allow_legacy and legacy_actor:
        return {
            'actor_id': legacy_actor,
            'actor_type': 'legacy_string_actor',
            'display_name': legacy_actor,
            'auth_subject': None,
            'auth_provider': None,
            'legacy': True,
            'raw_actor': legacy_actor,
        }

    raise ValueError('structured actor is required: provide actor{actor_id, actor_type} or actor_id + actor_type')


def _normalize_evidence_references(evidence_references):
    """Normalize outcome evidence references into a structured non-empty list."""
    if not isinstance(evidence_references, list) or not evidence_references:
        raise ValueError('outcome_evidence must contain at least one evidence reference')

    normalized = []
    for index, item in enumerate(evidence_references):
        if isinstance(item, str):
            value = _clean_text(item)
            if not value:
                raise ValueError(f'outcome_evidence[{index}] must not be empty')
            normalized.append({
                'ref_type': 'unspecified_reference',
                'ref_value': value,
                'label': None,
            })
            continue

        if not isinstance(item, dict):
            raise ValueError(f'outcome_evidence[{index}] must be a string or object')

        ref_type = _clean_text(item.get('ref_type') or item.get('type'))
        ref_value = _clean_text(item.get('ref_value') or item.get('value') or item.get('url') or item.get('id') or item.get('note_ref'))
        if not ref_type or not ref_value:
            raise ValueError(f'outcome_evidence[{index}] requires ref_type and ref_value')
        normalized.append({
            'ref_type': ref_type,
            'ref_value': ref_value,
            'label': _clean_text(item.get('label')) or None,
        })

    return normalized


def _normalize_verification_payload(verification=None):
    """Normalize verification scaffold payload without claiming verification exists."""
    verification = verification or {}
    if not isinstance(verification, dict):
        raise ValueError('verification must be an object when provided')

    status = _clean_text(verification.get('status') or 'unverified').lower() or 'unverified'
    if status not in VALID_VERIFICATION_STATUSES:
        raise ValueError('verification.status must be unverified, pending, verified, or disputed')

    return {
        'status': status,
        'path': _clean_text(verification.get('path')) or None,
        'notes': _clean_text(verification.get('notes')) or None,
    }


def _actor_display(actor_payload):
    """Collapse a structured actor payload into a readable label."""
    if not isinstance(actor_payload, dict):
        return None
    actor_type = _clean_text(actor_payload.get('actor_type'))
    actor_id = _clean_text(actor_payload.get('actor_id'))
    if actor_type and actor_id:
        return f'{actor_type}:{actor_id}'
    return actor_id or actor_type or None


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
                decision_actor TEXT,
                decision_actor_id TEXT,
                decision_actor_type TEXT,
                decision_actor_payload JSONB,
                decision_actor_is_legacy BOOLEAN NOT NULL DEFAULT FALSE,
                decided_at TIMESTAMPTZ,
                decision_notes TEXT,
                executed_at TIMESTAMPTZ,
                execution_status TEXT NOT NULL DEFAULT 'pending',
                execution_actor TEXT,
                execution_actor_id TEXT,
                execution_actor_type TEXT,
                execution_actor_payload JSONB,
                execution_actor_is_legacy BOOLEAN NOT NULL DEFAULT FALSE,
                execution_updated_at TIMESTAMPTZ,
                execution_notes TEXT,
                execution_verification_status TEXT NOT NULL DEFAULT 'unverified',
                execution_verification_path TEXT,
                execution_verification_notes TEXT,
                execution_verified_at TIMESTAMPTZ,
                outcome_type TEXT,
                outcome_value NUMERIC(12, 2),
                outcome_currency TEXT DEFAULT 'USD',
                outcome_notes TEXT,
                outcome_actor_id TEXT,
                outcome_actor_type TEXT,
                outcome_actor_payload JSONB,
                outcome_actor_is_legacy BOOLEAN NOT NULL DEFAULT FALSE,
                outcome_evidence JSONB NOT NULL DEFAULT '[]'::jsonb,
                outcome_evidence_count INTEGER NOT NULL DEFAULT 0,
                outcome_verification_status TEXT NOT NULL DEFAULT 'unverified',
                outcome_verification_path TEXT,
                outcome_verification_notes TEXT,
                outcome_verified_at TIMESTAMPTZ,
                measured_at TIMESTAMPTZ,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)
        cur.execute("ALTER TABLE saas_consequence_actions ADD COLUMN IF NOT EXISTS decision_actor TEXT")
        cur.execute("ALTER TABLE saas_consequence_actions ADD COLUMN IF NOT EXISTS decision_actor_id TEXT")
        cur.execute("ALTER TABLE saas_consequence_actions ADD COLUMN IF NOT EXISTS decision_actor_type TEXT")
        cur.execute("ALTER TABLE saas_consequence_actions ADD COLUMN IF NOT EXISTS decision_actor_payload JSONB")
        cur.execute("ALTER TABLE saas_consequence_actions ADD COLUMN IF NOT EXISTS decision_actor_is_legacy BOOLEAN NOT NULL DEFAULT FALSE")
        cur.execute("ALTER TABLE saas_consequence_actions ADD COLUMN IF NOT EXISTS decided_at TIMESTAMPTZ")
        cur.execute("ALTER TABLE saas_consequence_actions ADD COLUMN IF NOT EXISTS execution_actor TEXT")
        cur.execute("ALTER TABLE saas_consequence_actions ADD COLUMN IF NOT EXISTS execution_actor_id TEXT")
        cur.execute("ALTER TABLE saas_consequence_actions ADD COLUMN IF NOT EXISTS execution_actor_type TEXT")
        cur.execute("ALTER TABLE saas_consequence_actions ADD COLUMN IF NOT EXISTS execution_actor_payload JSONB")
        cur.execute("ALTER TABLE saas_consequence_actions ADD COLUMN IF NOT EXISTS execution_actor_is_legacy BOOLEAN NOT NULL DEFAULT FALSE")
        cur.execute("ALTER TABLE saas_consequence_actions ADD COLUMN IF NOT EXISTS execution_updated_at TIMESTAMPTZ")
        cur.execute("ALTER TABLE saas_consequence_actions ADD COLUMN IF NOT EXISTS execution_verification_status TEXT NOT NULL DEFAULT 'unverified'")
        cur.execute("ALTER TABLE saas_consequence_actions ADD COLUMN IF NOT EXISTS execution_verification_path TEXT")
        cur.execute("ALTER TABLE saas_consequence_actions ADD COLUMN IF NOT EXISTS execution_verification_notes TEXT")
        cur.execute("ALTER TABLE saas_consequence_actions ADD COLUMN IF NOT EXISTS execution_verified_at TIMESTAMPTZ")
        cur.execute("ALTER TABLE saas_consequence_actions ADD COLUMN IF NOT EXISTS outcome_actor_id TEXT")
        cur.execute("ALTER TABLE saas_consequence_actions ADD COLUMN IF NOT EXISTS outcome_actor_type TEXT")
        cur.execute("ALTER TABLE saas_consequence_actions ADD COLUMN IF NOT EXISTS outcome_actor_payload JSONB")
        cur.execute("ALTER TABLE saas_consequence_actions ADD COLUMN IF NOT EXISTS outcome_actor_is_legacy BOOLEAN NOT NULL DEFAULT FALSE")
        cur.execute("ALTER TABLE saas_consequence_actions ADD COLUMN IF NOT EXISTS outcome_evidence JSONB NOT NULL DEFAULT '[]'::jsonb")
        cur.execute("ALTER TABLE saas_consequence_actions ADD COLUMN IF NOT EXISTS outcome_evidence_count INTEGER NOT NULL DEFAULT 0")
        cur.execute("ALTER TABLE saas_consequence_actions ADD COLUMN IF NOT EXISTS outcome_verification_status TEXT NOT NULL DEFAULT 'unverified'")
        cur.execute("ALTER TABLE saas_consequence_actions ADD COLUMN IF NOT EXISTS outcome_verification_path TEXT")
        cur.execute("ALTER TABLE saas_consequence_actions ADD COLUMN IF NOT EXISTS outcome_verification_notes TEXT")
        cur.execute("ALTER TABLE saas_consequence_actions ADD COLUMN IF NOT EXISTS outcome_verified_at TIMESTAMPTZ")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_consequence_cases_domain_detected ON saas_consequence_cases(domain, detected_at DESC)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_consequence_cases_synthetic ON saas_consequence_cases(is_synthetic)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_consequence_actions_case ON saas_consequence_actions(case_id)")
        cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_consequence_actions_case_active ON saas_consequence_actions(case_id) WHERE approval_status IN ('pending', 'approved')")
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
    """Record a recommended action for a consequence case and return its id.

    Deduplication guard:
    if the case already has an action in pending or approved state, return that
    action instead of creating another open action for the same case.
    """
    pool = get_pool()
    conn = None
    try:
        conn = pool.getconn()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id::text
                FROM saas_consequence_actions
                WHERE case_id = %s
                  AND approval_status IN ('pending', 'approved')
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (case_id,),
            )
            existing = cur.fetchone()
            if existing:
                conn.commit()
                return existing['id']

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


def get_consequence_action(action_id):
    """Return one consequence action with its parent case context."""
    pool = get_pool()
    conn = None
    try:
        conn = pool.getconn()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT
                    a.id::text AS action_id,
                    a.case_id::text AS case_id,
                    a.recommendation,
                    a.causal_hypothesis,
                    a.requires_approval,
                    a.approval_status,
                    a.approved_by,
                    a.decision_actor,
                    a.decision_actor_id,
                    a.decision_actor_type,
                    a.decision_actor_payload,
                    a.decision_actor_is_legacy,
                    a.decided_at,
                    a.decision_notes,
                    a.execution_status,
                    a.execution_actor,
                    a.execution_actor_id,
                    a.execution_actor_type,
                    a.execution_actor_payload,
                    a.execution_actor_is_legacy,
                    a.execution_updated_at,
                    a.execution_notes,
                    a.execution_verification_status,
                    a.execution_verification_path,
                    a.execution_verification_notes,
                    a.execution_verified_at,
                    a.executed_at,
                    a.outcome_type,
                    a.outcome_value,
                    a.outcome_currency,
                    a.outcome_notes,
                    a.outcome_actor_id,
                    a.outcome_actor_type,
                    a.outcome_actor_payload,
                    a.outcome_actor_is_legacy,
                    a.outcome_evidence,
                    a.outcome_evidence_count,
                    a.outcome_verification_status,
                    a.outcome_verification_path,
                    a.outcome_verification_notes,
                    a.outcome_verified_at,
                    a.measured_at,
                    a.created_at,
                    c.domain,
                    c.source_system,
                    c.source_event_id,
                    c.anomaly_type,
                    c.is_synthetic,
                    c.detected_at
                FROM saas_consequence_actions a
                JOIN saas_consequence_cases c ON c.id = a.case_id
                WHERE a.id = %s
                LIMIT 1
                """,
                (action_id,),
            )
            row = cur.fetchone()
            return dict(row) if row else None
    finally:
        if conn:
            pool.putconn(conn)


def get_case_actions(case_id):
    """Return all actions for a case, newest first."""
    pool = get_pool()
    conn = None
    try:
        conn = pool.getconn()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT
                    id::text AS action_id,
                    case_id::text AS case_id,
                    recommendation,
                    causal_hypothesis,
                    requires_approval,
                    approval_status,
                    approved_by,
                    decision_actor,
                    decision_actor_id,
                    decision_actor_type,
                    decision_actor_payload,
                    decision_actor_is_legacy,
                    decided_at,
                    decision_notes,
                    execution_status,
                    execution_actor,
                    execution_actor_id,
                    execution_actor_type,
                    execution_actor_payload,
                    execution_actor_is_legacy,
                    execution_updated_at,
                    execution_notes,
                    execution_verification_status,
                    execution_verification_path,
                    execution_verification_notes,
                    execution_verified_at,
                    executed_at,
                    outcome_type,
                    outcome_value,
                    outcome_currency,
                    outcome_notes,
                    outcome_actor_id,
                    outcome_actor_type,
                    outcome_actor_payload,
                    outcome_actor_is_legacy,
                    outcome_evidence,
                    outcome_evidence_count,
                    outcome_verification_status,
                    outcome_verification_path,
                    outcome_verification_notes,
                    outcome_verified_at,
                    measured_at,
                    created_at
                FROM saas_consequence_actions
                WHERE case_id = %s
                ORDER BY created_at DESC
                """,
                (case_id,),
            )
            return [dict(row) for row in cur.fetchall()]
    finally:
        if conn:
            pool.putconn(conn)


def record_action_decision(action_id, approval_status, approved_by=None, decision_notes=None, actor=None, actor_id=None, actor_type=None):
    """Record approval or rejection for a consequence action."""
    if approval_status not in {'approved', 'rejected'}:
        raise ValueError('approval_status must be approved or rejected')
    actor_payload = _normalize_actor_payload(actor=actor or approved_by, actor_id=actor_id, actor_type=actor_type, allow_legacy=True)
    actor_label = _actor_display(actor_payload)

    action = get_consequence_action(action_id)
    if not action:
        raise ValueError('action not found')
    if action.get('approval_status') != 'pending':
        raise ValueError('only pending actions can be approved or rejected')

    pool = get_pool()
    conn = None
    try:
        conn = pool.getconn()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                UPDATE saas_consequence_actions
                SET approval_status = %s,
                    approved_by = CASE WHEN %s = 'approved' THEN %s ELSE NULL END,
                    decision_actor = %s,
                    decision_actor_id = %s,
                    decision_actor_type = %s,
                    decision_actor_payload = %s::jsonb,
                    decision_actor_is_legacy = %s,
                    decided_at = NOW(),
                    decision_notes = %s
                WHERE id = %s
                RETURNING id::text AS action_id
                """,
                (
                    approval_status,
                    approval_status,
                    actor_label if approval_status == 'approved' else None,
                    actor_label,
                    actor_payload['actor_id'],
                    actor_payload['actor_type'],
                    json.dumps(actor_payload),
                    actor_payload['legacy'],
                    decision_notes,
                    action_id,
                ),
            )
            row = cur.fetchone()
            conn.commit()
            return get_consequence_action(row['action_id']) if row else None
    finally:
        if conn:
            pool.putconn(conn)


def record_action_execution(action_id, execution_status, execution_notes=None, execution_actor=None, actor=None, actor_id=None, actor_type=None, verification=None):
    """Record execution status for a consequence action."""
    if execution_status not in VALID_EXECUTION_STATUSES:
        raise ValueError('execution_status must be pending, executed, or failed')
    actor_payload = _normalize_actor_payload(actor=actor or execution_actor, actor_id=actor_id, actor_type=actor_type, allow_legacy=True)
    actor_label = _actor_display(actor_payload)
    verification_payload = _normalize_verification_payload(verification)

    action = get_consequence_action(action_id)
    if not action:
        raise ValueError('action not found')
    if action.get('approval_status') != 'approved':
        raise ValueError('only approved actions can move through execution')

    pool = get_pool()
    conn = None
    try:
        conn = pool.getconn()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                UPDATE saas_consequence_actions
                SET execution_status = %s,
                    execution_notes = %s,
                    execution_actor = %s,
                    execution_actor_id = %s,
                    execution_actor_type = %s,
                    execution_actor_payload = %s::jsonb,
                    execution_actor_is_legacy = %s,
                    execution_updated_at = NOW(),
                    execution_verification_status = %s,
                    execution_verification_path = %s,
                    execution_verification_notes = %s,
                    execution_verified_at = CASE WHEN %s = 'verified' THEN NOW() ELSE NULL END,
                    executed_at = CASE
                        WHEN %s IN ('executed', 'failed') THEN NOW()
                        WHEN %s = 'pending' THEN NULL
                        ELSE executed_at
                    END
                WHERE id = %s
                RETURNING id::text AS action_id
                """,
                (
                    execution_status,
                    execution_notes,
                    actor_label,
                    actor_payload['actor_id'],
                    actor_payload['actor_type'],
                    json.dumps(actor_payload),
                    actor_payload['legacy'],
                    verification_payload['status'],
                    verification_payload['path'],
                    verification_payload['notes'],
                    verification_payload['status'],
                    execution_status,
                    execution_status,
                    action_id,
                ),
            )
            row = cur.fetchone()
            conn.commit()
            return get_consequence_action(row['action_id']) if row else None
    finally:
        if conn:
            pool.putconn(conn)


def record_action_outcome(action_id, outcome_type, outcome_value=None, outcome_notes=None, outcome_currency='USD', actor=None, actor_id=None, actor_type=None, outcome_evidence=None, verification=None):
    """Record measured outcome for a consequence action."""
    outcome_type = (outcome_type or '').strip()
    if not outcome_type:
        raise ValueError('outcome_type is required')
    actor_payload = _normalize_actor_payload(actor=actor, actor_id=actor_id, actor_type=actor_type, allow_legacy=True)
    evidence_payload = _normalize_evidence_references(outcome_evidence)
    verification_payload = _normalize_verification_payload(verification)

    action = get_consequence_action(action_id)
    if not action:
        raise ValueError('action not found')
    if action.get('execution_status') != 'executed':
        raise ValueError('only executed actions can receive measured outcomes')

    pool = get_pool()
    conn = None
    try:
        conn = pool.getconn()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                UPDATE saas_consequence_actions
                SET outcome_type = %s,
                    outcome_value = %s,
                    outcome_currency = %s,
                    outcome_notes = %s,
                    outcome_actor_id = %s,
                    outcome_actor_type = %s,
                    outcome_actor_payload = %s::jsonb,
                    outcome_actor_is_legacy = %s,
                    outcome_evidence = %s::jsonb,
                    outcome_evidence_count = %s,
                    outcome_verification_status = %s,
                    outcome_verification_path = %s,
                    outcome_verification_notes = %s,
                    outcome_verified_at = CASE WHEN %s = 'verified' THEN NOW() ELSE NULL END,
                    measured_at = NOW()
                WHERE id = %s
                RETURNING id::text AS action_id
                """,
                (
                    outcome_type,
                    outcome_value,
                    outcome_currency,
                    outcome_notes,
                    actor_payload['actor_id'],
                    actor_payload['actor_type'],
                    json.dumps(actor_payload),
                    actor_payload['legacy'],
                    json.dumps(evidence_payload),
                    len(evidence_payload),
                    verification_payload['status'],
                    verification_payload['path'],
                    verification_payload['notes'],
                    verification_payload['status'],
                    action_id,
                ),
            )
            row = cur.fetchone()
            conn.commit()
            return get_consequence_action(row['action_id']) if row else None
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
                    COUNT(a.id) FILTER (WHERE a.approval_status = 'rejected')::int AS rejected_actions,
                    COUNT(a.id) FILTER (WHERE a.execution_status = 'executed')::int AS executed_actions,
                    COUNT(a.id) FILTER (WHERE a.execution_status = 'failed')::int AS failed_actions,
                    COUNT(a.id) FILTER (WHERE a.outcome_type IS NOT NULL)::int AS measured_outcomes,
                    COUNT(a.id) FILTER (WHERE COALESCE(a.outcome_evidence_count, 0) > 0)::int AS evidenced_outcomes,
                    COUNT(a.id) FILTER (WHERE a.execution_verification_status = 'verified')::int AS execution_verified_actions,
                    COUNT(a.id) FILTER (WHERE a.outcome_verification_status = 'verified')::int AS outcome_verified_actions
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


def get_recent_consequence_actions(domain='revenue_recovery', limit=20):
    """Return recent action lifecycle entries for operator inspection."""
    pool = get_pool()
    conn = None
    try:
        conn = pool.getconn()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT
                    a.id::text AS action_id,
                    a.case_id::text AS case_id,
                    c.anomaly_type,
                    c.source_system,
                    c.is_synthetic,
                    a.recommendation,
                    a.requires_approval,
                    a.approval_status,
                    a.approved_by,
                    a.decision_actor,
                    a.decision_actor_id,
                    a.decision_actor_type,
                    a.decision_actor_payload,
                    a.decision_actor_is_legacy,
                    a.decided_at,
                    a.decision_notes,
                    a.execution_status,
                    a.execution_actor,
                    a.execution_actor_id,
                    a.execution_actor_type,
                    a.execution_actor_payload,
                    a.execution_actor_is_legacy,
                    a.execution_updated_at,
                    a.execution_notes,
                    a.execution_verification_status,
                    a.execution_verification_path,
                    a.execution_verification_notes,
                    a.execution_verified_at,
                    a.executed_at,
                    a.outcome_type,
                    a.outcome_value,
                    a.outcome_currency,
                    a.outcome_notes,
                    a.outcome_actor_id,
                    a.outcome_actor_type,
                    a.outcome_actor_payload,
                    a.outcome_actor_is_legacy,
                    a.outcome_evidence,
                    a.outcome_evidence_count,
                    a.outcome_verification_status,
                    a.outcome_verification_path,
                    a.outcome_verification_notes,
                    a.outcome_verified_at,
                    a.measured_at,
                    a.created_at
                FROM saas_consequence_actions a
                JOIN saas_consequence_cases c ON c.id = a.case_id
                WHERE c.domain = %s
                ORDER BY a.created_at DESC
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
                    COUNT(a.id) FILTER (WHERE c.is_synthetic = FALSE AND COALESCE(a.outcome_evidence_count, 0) > 0)::int AS real_evidenced_outcomes,
                    COUNT(a.id) FILTER (WHERE c.is_synthetic = FALSE AND a.execution_verification_status = 'verified')::int AS real_execution_verified_actions,
                    COUNT(a.id) FILTER (WHERE c.is_synthetic = FALSE AND a.outcome_verification_status = 'verified')::int AS real_outcome_verified_actions,
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
                'recent_actions': get_recent_consequence_actions(domain, limit=20),
            }
    finally:
        if conn:
            pool.putconn(conn)
