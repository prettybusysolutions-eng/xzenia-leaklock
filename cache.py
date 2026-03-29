"""
DB-backed scan cache — replaces fragile in-memory SCAN_CACHE dict.
Uses psycopg2 connection pool passed from caller.
"""
import json
from datetime import datetime, timedelta, timezone


def cache_get(pool, key: str):
    """Fetch a cached value by key. Returns dict or None if missing/expired."""
    conn = pool.getconn()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT payload FROM scan_cache WHERE cache_key = %s AND (expires_at IS NULL OR expires_at > NOW())",
            (key,)
        )
        row = cur.fetchone()
        return row[0] if row else None
    finally:
        pool.putconn(conn)


def cache_set(pool, key: str, value: dict, ttl_seconds: int = 3600):
    """Store a value in the cache with an optional TTL (default 1 hour)."""
    conn = pool.getconn()
    try:
        expires = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO scan_cache (cache_key, payload, expires_at)
               VALUES (%s, %s::jsonb, %s)
               ON CONFLICT (cache_key) DO UPDATE
               SET payload = EXCLUDED.payload, expires_at = EXCLUDED.expires_at""",
            (key, json.dumps(value), expires)
        )
        conn.commit()
    finally:
        pool.putconn(conn)
