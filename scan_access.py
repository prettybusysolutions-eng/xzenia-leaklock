"""Signed, expiring access tokens for scan-owned routes."""

from functools import wraps

from flask import jsonify, request
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from config import SCAN_ACCESS_MAX_AGE, SECRET_KEY


_SALT = "leaklock-scan-access-v1"


def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(SECRET_KEY, salt=_SALT)


def create_scan_access_token(scan_id: str) -> str:
    if not scan_id:
        raise ValueError("scan_id is required")
    return _serializer().dumps({"scan_id": scan_id})


def verify_scan_access_token(scan_id: str, token: str) -> bool:
    if not scan_id or not token:
        return False
    try:
        payload = _serializer().loads(token, max_age=SCAN_ACCESS_MAX_AGE)
    except (BadSignature, SignatureExpired):
        return False
    return isinstance(payload, dict) and payload.get("scan_id") == scan_id


def request_access_token() -> str:
    return (
        request.args.get("access_token", "").strip()
        or request.form.get("access_token", "").strip()
        or request.headers.get("X-Scan-Access-Token", "").strip()
    )


def require_scan_access(view):
    """Require a valid token bound to the scan ID in route, form, or query."""

    @wraps(view)
    def decorated(*args, **kwargs):
        route_scan_id = request.view_args.get("scan_id", "") if request.view_args else ""
        scan_id = str(kwargs.get("scan_id") or route_scan_id).strip()
        if not scan_id:
            scan_id = (
                request.form.get("scan_id", "").strip()
                or request.args.get("scan_id", "").strip()
            )
        if not verify_scan_access_token(scan_id, request_access_token()):
            if request.accept_mimetypes.best == "application/json":
                return jsonify({"error": "scan_access_denied"}), 403
            return (
                "<h1>Access denied</h1>"
                "<p>This scan link is missing, invalid, or expired.</p>",
                403,
            )
        return view(*args, **kwargs)

    return decorated

