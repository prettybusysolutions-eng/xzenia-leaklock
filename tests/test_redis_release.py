import os
import uuid

import pytest
from app import create_app


def test_two_app_instances_share_rate_limit(monkeypatch):
    url = os.environ.get('RELEASE_TEST_REDIS_URL')
    if not url:
        pytest.skip('RELEASE_TEST_REDIS_URL required')
    monkeypatch.setenv('LEAKLOCK_REDIS_URL', url)
    path = '/release-rate-' + uuid.uuid4().hex
    apps = [create_app(), create_app()]
    for app in apps:
        app.add_url_rule(path, endpoint=path, view_func=lambda: 'ok')
    clients = [app.test_client() for app in apps]
    for index in range(50):
        assert clients[index % 2].get(path).status_code == 200
    assert clients[0].get(path).status_code == 429
    assert clients[1].get(path).status_code == 429
    # Health probes must not consume the visitor quota.
    for _ in range(55):
        assert clients[0].get('/live').status_code == 200


def test_production_requires_shared_storage(monkeypatch):
    monkeypatch.setenv('LEAKLOCK_ENV', 'production')
    monkeypatch.delenv('LEAKLOCK_REDIS_URL', raising=False)
    with pytest.raises(RuntimeError, match='LEAKLOCK_REDIS_URL'):
        create_app()
