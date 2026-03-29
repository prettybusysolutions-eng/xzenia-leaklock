"""Tests for System 6 proof, intake, and lifecycle routes."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from models.db import add_consequence_action, record_action_decision, record_action_outcome
from services.consequence import (
    build_revenue_recovery_evidence,
    ingest_scan_result_to_consequence_cases,
    infer_synthetic_flag,
    is_sample_csv_upload,
    validate_revenue_recovery_evidence,
)


def _example_scan(scan_id='scan-123'):
    return {
        'scan_id': scan_id,
        'rows_parsed': 12,
        'total_revenue': 2400.0,
        'total_leakage': 500.0,
        'scanned_at': '2026-03-29T15:40:00+00:00',
        'leaks': [
            {
                'pattern': 'failed_payment_neglect',
                'pattern_name': 'Failed Payment Neglect',
                'description': '2 failed payments with no recovery detected',
                'amount_estimate': 500,
                'confidence': 0.9,
                'severity': 'high',
                'affected_rows': 2,
                'details': {'failed_count': 2},
            }
        ],
    }


class _FakeCursor:
    def __init__(self, responses):
        self.responses = list(responses)
        self.executed = []

    def execute(self, query, params=None):
        self.executed.append((' '.join(query.split()), params))

    def fetchone(self):
        if self.responses:
            return self.responses.pop(0)
        return None

    def fetchall(self):
        if self.responses:
            return self.responses.pop(0)
        return []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class _FakeConn:
    def __init__(self, responses):
        self.cursor_instance = _FakeCursor(responses)
        self.committed = 0

    def cursor(self, cursor_factory=None):
        return self.cursor_instance

    def commit(self):
        self.committed += 1


class _FakePool:
    def __init__(self, responses):
        self.conn = _FakeConn(responses)
        self.returned = 0

    def getconn(self):
        return self.conn

    def putconn(self, conn):
        self.returned += 1


def test_evidence_validator_accepts_example_payload():
    scan = _example_scan()
    leak = scan['leaks'][0]
    payload = build_revenue_recovery_evidence(
        scan_result=scan,
        leak=leak,
        source_system='file_upload',
        source_kind='file_upload',
        source_event_id='scan-123:failed_payment_neglect',
        is_synthetic=False,
    )

    is_valid, errors = validate_revenue_recovery_evidence(payload)
    assert is_valid is True
    assert errors == []
    assert payload['estimated_impact']['basis'] == 'scan_estimate_only_not_realized_outcome'


def test_intake_creates_real_case_records(monkeypatch):
    created = []
    actions = []

    def fake_create_consequence_case(**kwargs):
        created.append(kwargs)
        return f"case-{len(created)}"

    def fake_add_consequence_action(case_id, recommendation, causal_hypothesis=None, requires_approval=True):
        actions.append({
            'case_id': case_id,
            'recommendation': recommendation,
            'causal_hypothesis': causal_hypothesis,
            'requires_approval': requires_approval,
        })
        return f"action-{len(actions)}"

    monkeypatch.setattr('services.consequence.create_consequence_case', fake_create_consequence_case)
    monkeypatch.setattr('services.consequence.add_consequence_action', fake_add_consequence_action)

    results = ingest_scan_result_to_consequence_cases(
        _example_scan(),
        source_system='file_upload',
        source_kind='file_upload',
        explicit_is_synthetic=False,
    )

    assert len(results) == 1
    assert created[0]['is_synthetic'] is False
    assert created[0]['evidence']['is_synthetic'] is False
    assert created[0]['evidence']['domain'] == 'revenue_recovery'
    assert actions[0]['requires_approval'] is True
    assert results[0]['action_id'] == 'action-1'


def test_demo_sample_paths_are_synthetic():
    assert infer_synthetic_flag('demo_sample') is True
    assert infer_synthetic_flag('file_upload') is False


def test_sample_csv_fingerprint_marks_upload_synthetic():
    with open('static/sample_data.csv', 'rb') as f:
        raw = f.read()
    assert is_sample_csv_upload(raw) is True
    assert infer_synthetic_flag('file_upload', raw_bytes=raw) is True


def test_add_consequence_action_dedupes_existing_open_action(monkeypatch):
    fake_pool = _FakePool([
        {'id': 'action-existing'},
    ])
    monkeypatch.setattr('models.db.get_pool', lambda: fake_pool)

    action_id = add_consequence_action(
        'case-1',
        recommendation='Retry card updater and contact customer.',
        causal_hypothesis='Card updater failed.',
        requires_approval=True,
    )

    assert action_id == 'action-existing'
    executed_queries = fake_pool.conn.cursor_instance.executed
    assert len(executed_queries) == 1
    assert 'SELECT id::text' in executed_queries[0][0]
    assert fake_pool.conn.committed == 1


def test_app_boots_and_proof_report_route_works(monkeypatch):
    monkeypatch.setattr(
        'routes.api.get_proof_report',
        lambda domain: {
            'domain': domain,
            'proof_boundary': {
                'counts_as_proof': 'non_synthetic_cases_only',
                'excluded_from_proof': 'demo_sample_seed_test_cases',
            },
            'cases': {'real_cases': 1, 'synthetic_cases': 2, 'total_cases': 3},
            'actions': {'real_actions': 0, 'synthetic_actions': 0},
            'proof_metrics': {
                'real_cases': 1,
                'detected_cases': 1,
                'recommended_actions': 1,
                'approved_actions': 0,
                'executed_actions': 0,
                'measured_outcomes': 0,
                'realized_value': 0,
            },
            'recent_cases': [],
            'recent_actions': [],
        },
    )

    app = create_app()
    app.config['WTF_CSRF_ENABLED'] = False
    client = app.test_client()
    response = client.get('/api/system6/proof/revenue-recovery')

    assert response.status_code == 200
    data = response.get_json()
    assert data['domain'] == 'revenue_recovery'
    assert data['cases']['real_cases'] == 1
    assert data['cases']['synthetic_cases'] == 2

    page = client.get('/ops/system6/proof/revenue-recovery')
    assert page.status_code == 200
    assert b'System 6 Proof' in page.data
    assert b'Action lifecycle' in page.data


def test_approval_route_records_human_decision(monkeypatch):
    monkeypatch.setattr(
        'routes.api.record_action_decision',
        lambda action_id, approval_status, approved_by=None, decision_notes=None, actor=None, actor_id=None, actor_type=None: {
            'action_id': action_id,
            'approval_status': approval_status,
            'approved_by': approved_by,
            'decision_notes': decision_notes,
            'decision_actor_payload': actor,
            'decision_actor_id': actor_id,
            'decision_actor_type': actor_type,
        },
    )

    app = create_app()
    app.config['WTF_CSRF_ENABLED'] = False
    client = app.test_client()
    response = client.post(
        '/api/system6/actions/action-1/decision',
        json={
            'approval_status': 'approved',
            'actor': {
                'actor_id': 'user-123',
                'actor_type': 'human_operator',
                'display_name': 'Kamm',
            },
            'notes': 'Approved after manual evidence review.',
        },
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data['ok'] is True
    assert data['action']['approval_status'] == 'approved'
    assert data['action']['decision_actor_payload']['actor_id'] == 'user-123'
    assert data['action']['decision_actor_payload']['actor_type'] == 'human_operator'


def test_execution_route_records_execution_status(monkeypatch):
    monkeypatch.setattr(
        'routes.api.record_action_execution',
        lambda action_id, execution_status, execution_notes=None, execution_actor=None, actor=None, actor_id=None, actor_type=None, verification=None: {
            'action_id': action_id,
            'execution_status': execution_status,
            'execution_notes': execution_notes,
            'execution_actor': execution_actor,
            'execution_actor_payload': actor,
            'execution_actor_id': actor_id,
            'execution_actor_type': actor_type,
            'execution_verification_status': (verification or {}).get('status', 'unverified') if isinstance(verification, dict) else 'unverified',
        },
    )

    app = create_app()
    app.config['WTF_CSRF_ENABLED'] = False
    client = app.test_client()
    response = client.post(
        '/api/system6/actions/action-1/execution',
        json={
            'execution_status': 'executed',
            'actor_id': 'ops-7',
            'actor_type': 'operations_user',
            'notes': 'Customer outreach completed.',
            'verification': {
                'status': 'pending',
                'path': 'crm.timeline',
            },
        },
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data['ok'] is True
    assert data['action']['execution_status'] == 'executed'
    assert data['action']['execution_actor_id'] == 'ops-7'
    assert data['action']['execution_actor_type'] == 'operations_user'
    assert data['action']['execution_verification_status'] == 'pending'


def test_outcome_route_records_measured_outcome(monkeypatch):
    monkeypatch.setattr(
        'routes.api.record_action_outcome',
        lambda action_id, outcome_type, outcome_value=None, outcome_notes=None, outcome_currency='USD', actor=None, actor_id=None, actor_type=None, outcome_evidence=None, verification=None: {
            'action_id': action_id,
            'outcome_type': outcome_type,
            'outcome_value': outcome_value,
            'outcome_notes': outcome_notes,
            'outcome_currency': outcome_currency,
            'outcome_actor_payload': actor,
            'outcome_actor_id': actor_id,
            'outcome_actor_type': actor_type,
            'outcome_evidence': outcome_evidence,
            'outcome_evidence_count': len(outcome_evidence or []),
            'outcome_verification_status': (verification or {}).get('status', 'unverified') if isinstance(verification, dict) else 'unverified',
        },
    )

    app = create_app()
    app.config['WTF_CSRF_ENABLED'] = False
    client = app.test_client()
    response = client.post(
        '/api/system6/actions/action-1/outcome',
        json={
            'outcome_type': 'recovered_revenue',
            'outcome_value': 500.00,
            'outcome_notes': 'Customer paid recovered invoice.',
            'outcome_currency': 'USD',
            'actor_id': 'ops-7',
            'actor_type': 'operations_user',
            'outcome_evidence': [
                {'ref_type': 'document_url', 'ref_value': 'https://example.com/invoices/paid-123'}
            ],
            'verification': {
                'status': 'pending',
                'path': 'stripe.payment_event',
            },
        },
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data['ok'] is True
    assert data['action']['outcome_type'] == 'recovered_revenue'
    assert data['action']['outcome_value'] == 500.0
    assert data['action']['outcome_evidence_count'] == 1
    assert data['action']['outcome_verification_status'] == 'pending'


def test_approval_route_rejects_missing_structured_actor(monkeypatch):
    monkeypatch.setattr(
        'routes.api.record_action_decision',
        lambda *args, **kwargs: (_ for _ in ()).throw(ValueError('structured actor is required: provide actor{actor_id, actor_type} or actor_id + actor_type')),
    )

    app = create_app()
    app.config['WTF_CSRF_ENABLED'] = False
    client = app.test_client()
    response = client.post(
        '/api/system6/actions/action-1/decision',
        json={
            'approval_status': 'approved',
            'notes': 'No actor supplied.',
        },
    )

    assert response.status_code == 400
    data = response.get_json()
    assert data['error'] == 'invalid_action_decision'
    assert 'structured actor is required' in data['detail']


def test_outcome_route_requires_evidence_reference(monkeypatch):
    monkeypatch.setattr(
        'routes.api.record_action_outcome',
        lambda *args, **kwargs: (_ for _ in ()).throw(ValueError('outcome_evidence must contain at least one evidence reference')),
    )

    app = create_app()
    app.config['WTF_CSRF_ENABLED'] = False
    client = app.test_client()
    response = client.post(
        '/api/system6/actions/action-1/outcome',
        json={
            'outcome_type': 'recovered_revenue',
            'outcome_value': 500.00,
            'actor_id': 'ops-7',
            'actor_type': 'operations_user',
            'outcome_evidence': [],
        },
    )

    assert response.status_code == 400
    data = response.get_json()
    assert data['error'] == 'invalid_action_outcome'
    assert 'outcome_evidence must contain at least one evidence reference' in data['detail']


def test_record_action_decision_marks_legacy_string_actor(monkeypatch):
    fake_pool = _FakePool([{'action_id': 'action-legacy'}])
    monkeypatch.setattr('models.db.get_pool', lambda: fake_pool)
    monkeypatch.setattr('models.db.get_consequence_action', lambda action_id: {'action_id': action_id, 'approval_status': 'pending'})

    result = record_action_decision(
        'action-legacy',
        approval_status='approved',
        approved_by='human:legacy-operator',
        decision_notes='Legacy compatibility path.',
    )

    assert result['action_id'] == 'action-legacy'
    query, params = fake_pool.conn.cursor_instance.executed[0]
    assert 'decision_actor_payload' in query
    assert params[4] == 'human:legacy-operator'
    assert params[5] == 'legacy_string_actor'
    assert params[7] is True


def test_record_action_outcome_requires_evidence_and_records_verification(monkeypatch):
    fake_pool = _FakePool([{'action_id': 'action-outcome'}])
    monkeypatch.setattr('models.db.get_pool', lambda: fake_pool)
    monkeypatch.setattr('models.db.get_consequence_action', lambda action_id: {'action_id': action_id, 'execution_status': 'executed'})

    result = record_action_outcome(
        'action-outcome',
        outcome_type='recovered_revenue',
        outcome_value=500.0,
        outcome_notes='Documented recovery.',
        actor_id='ops-9',
        actor_type='operations_user',
        outcome_evidence=[{'ref_type': 'source_record_id', 'ref_value': 'invoice-123'}],
        verification={'status': 'pending', 'path': 'stripe.invoice'},
    )

    assert result['action_id'] == 'action-outcome'
    query, params = fake_pool.conn.cursor_instance.executed[0]
    assert 'outcome_evidence' in query
    assert params[4] == 'ops-9'
    assert params[5] == 'operations_user'
    assert params[9] == 1
    assert params[10] == 'pending'

    try:
        record_action_outcome(
            'action-outcome',
            outcome_type='recovered_revenue',
            actor_id='ops-9',
            actor_type='operations_user',
            outcome_evidence=[],
        )
    except ValueError as exc:
        assert 'outcome_evidence must contain at least one evidence reference' in str(exc)
    else:
        raise AssertionError('Expected missing evidence to fail')
