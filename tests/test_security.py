"""Security and production-readiness regression tests."""

import hashlib

import routes.api as api_routes
from app import create_app
from scan_access import create_scan_access_token, verify_scan_access_token


class _Cursor:
    def __init__(self, fail=False):
        self.fail = fail

    def execute(self, _query):
        if self.fail:
            raise RuntimeError("database unavailable")

    def fetchone(self):
        return (1,)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class _Connection:
    def __init__(self, fail=False):
        self.fail = fail

    def cursor(self):
        return _Cursor(self.fail)


class _Pool:
    def __init__(self, fail=False):
        self.connection = _Connection(fail)

    def getconn(self):
        return self.connection

    def putconn(self, _connection):
        return None


def _app():
    app = create_app()
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    return app


def test_scan_access_token_is_bound_to_scan():
    token = create_scan_access_token("scan-12345678")
    assert verify_scan_access_token("scan-12345678", token) is True
    assert verify_scan_access_token("scan-other", token) is False
    assert verify_scan_access_token("scan-12345678", token + "forged") is False


def test_results_and_reports_require_signed_scan_access(monkeypatch):
    scan = {
        "scan_id": "scan-12345678",
        "rows_parsed": 1,
        "total_revenue": 100,
        "total_leakage": 10,
        "patterns_triggered": 0,
        "leaks": [],
    }
    monkeypatch.setattr("routes.pages.get_scan_by_id", lambda _scan_id: scan)
    monkeypatch.setattr("routes.api.get_scan_by_id", lambda _scan_id: scan)
    client = _app().test_client()

    assert client.get("/results/scan-12345678").status_code == 403
    assert client.get("/report/scan-12345678").status_code == 403

    token = create_scan_access_token("scan-12345678")
    assert client.get(
        "/results/scan-12345678", query_string={"access_token": token}
    ).status_code == 200
    assert client.get(
        "/report/scan-12345678", query_string={"access_token": token}
    ).status_code == 200


def test_system6_routes_reject_anonymous_requests():
    client = _app().test_client()
    protected = [
        ("get", "/api/system6/actions/action-1"),
        ("get", "/api/system6/cases/case-1/actions"),
        ("post", "/api/system6/actions/action-1/decision"),
        ("post", "/api/system6/actions/action-1/execution"),
        ("post", "/api/system6/actions/action-1/outcome"),
        ("get", "/api/system6/proof/revenue-recovery"),
        ("get", "/ops/system6/proof/revenue-recovery"),
        ("post", "/api/save-results"),
        ("get", "/scan/stripe-direct/json"),
    ]
    for method, path in protected:
        response = getattr(client, method)(path)
        assert response.status_code in {401, 403}, path


def test_system6_route_accepts_registered_api_key(monkeypatch):
    raw_key = "test-api-key"
    monkeypatch.setattr(
        api_routes,
        "_API_KEYS",
        {hashlib.sha256(raw_key.encode()).hexdigest(): "test"},
    )
    monkeypatch.setattr(api_routes, "_api_keys_loaded", True)
    monkeypatch.setattr(
        api_routes,
        "get_proof_report",
        lambda domain: {"domain": domain, "proof_metrics": {}},
    )
    client = _app().test_client()
    response = client.get(
        "/api/system6/proof/revenue-recovery",
        headers={"X-API-Key": raw_key},
    )
    assert response.status_code == 200
    assert response.get_json()["domain"] == "revenue_recovery"


def test_liveness_and_dependency_aware_readiness(monkeypatch):
    client = _app().test_client()
    assert client.get("/live").status_code == 200

    monkeypatch.setattr("models.db.get_pool", lambda: _Pool())
    ready = client.get("/health")
    assert ready.status_code == 200
    assert ready.get_json()["database"] == "ok"

    monkeypatch.setattr("models.db.get_pool", lambda: _Pool(fail=True))
    unavailable = client.get("/health")
    assert unavailable.status_code == 503
    assert unavailable.get_json()["database"] == "unavailable"



def test_signed_but_wrong_payload_shape_is_rejected():
    from scan_access import _serializer
    assert verify_scan_access_token("scan-12345678", _serializer().dumps(["scan-12345678"])) is False


def test_expired_token_is_rejected(monkeypatch):
    import scan_access
    token = create_scan_access_token("scan-12345678")
    monkeypatch.setattr(scan_access, "SCAN_ACCESS_MAX_AGE", -1)
    assert verify_scan_access_token("scan-12345678", token) is False


def test_production_rejects_empty_and_default_secret():
    import os
    import subprocess
    import sys
    for secret in ["", "leaklock-dev-key-change-in-prod-2026"]:
        env = dict(os.environ, LEAKLOCK_ENV="production", FLASK_SECRET_KEY=secret)
        result = subprocess.run([sys.executable, "-c", "import config"], env=env, capture_output=True)
        assert result.returncode != 0
        assert b"FLASK_SECRET_KEY must be configured" in result.stderr
