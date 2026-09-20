"""Cloud database credentials and transport settings survive connection setup."""
import pytest
import psycopg2

from config import _build_db_config
from models import db


def test_database_url_decodes_credentials_and_preserves_tls(monkeypatch):
    monkeypatch.setenv(
        'DATABASE_URL',
        'postgresql://release%40runner:p%40ss%3Aword%2Fvalue@db.example:5432/'
        'release_staging?sslmode=verify-full&sslrootcert=%2Fetc%2Fca.pem'
        '&connect_timeout=7&application_name=leaklock-staging',
    )
    config = _build_db_config()
    assert config['user'] == 'release@runner'
    assert config['password'] == 'p@ss:word/value'
    assert config['sslmode'] == 'verify-full'
    assert config['sslrootcert'] == '/etc/ca.pem'
    assert config['connect_timeout'] == '7'
    assert config['application_name'] == 'leaklock-staging'
    calls = []
    sentinel = object()

    def connect(*args, **kwargs):
        calls.append(kwargs)
        return sentinel

    monkeypatch.setattr(db, 'DB_CONFIG', config)
    monkeypatch.setattr(db, '_pool', None)
    monkeypatch.setattr(db.psycopg2, 'connect', connect)
    monkeypatch.setattr(db.psycopg2.pool, 'SimpleConnectionPool', connect)
    assert db.get_db() is sentinel
    assert db.get_pool() is sentinel
    assert calls == [config, config]


def test_malformed_database_url_fails_instead_of_using_local_defaults(monkeypatch):
    monkeypatch.setenv('DATABASE_URL', 'not a database URL')
    with pytest.raises(psycopg2.ProgrammingError):
        _build_db_config()


def test_individual_development_settings_remain_supported(monkeypatch):
    monkeypatch.delenv('DATABASE_URL', raising=False)
    for key, value in {'DB_HOST': 'localhost', 'DB_NAME': 'test_db',
                       'DB_USER': 'tester', 'DB_PASSWORD': 'test-only',
                       'DB_PORT': '5433'}.items():
        monkeypatch.setenv(key, value)
    assert _build_db_config() == dict(host='localhost', dbname='test_db',
                                    user='tester', password='test-only', port=5433)
