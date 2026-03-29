"""Cache service for LeakLock - wraps existing cache functionality."""
import json
import time
from config import CACHE_TTL, SCAN_RESULT_TTL
from models.db import get_pool


def cache_get(key: str):
    """Get value from cache (from Redis or fallback)."""
    from cache import cache_get as original_cache_get
    pool = get_pool()
    return original_cache_get(pool, key)


def cache_set(key: str, value: dict, ttl: int = None):
    """Set value in cache with TTL."""
    from cache import cache_set as original_cache_set
    pool = get_pool()
    return original_cache_set(pool, key, value, ttl or SCAN_RESULT_TTL)
