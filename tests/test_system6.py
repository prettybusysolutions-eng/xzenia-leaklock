"""Tests for System 6 Layer 2 proof + intake."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from services.consequence import (
    build_revenue_recovery_evidence,
    ingest_scan_result_to_consequence_cases,
    infer_synthetic_flag,
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

    def fake_create_consequence_case(**kwargs):
        created.append(kwargs)
        return f"case-{len(created)}"

    monkeypatch.setattr('services.consequence.create_consequence_case', fake_create_consequence_case)

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


def test_demo_sample_paths_are_synthetic():
    assert infer_synthetic_flag('demo_sample') is True
    assert infer_synthetic_flag('file_upload') is False


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
            'proof_metrics': {'real_cases': 1, 'detected_cases': 1},
        },
    )

    app = create_app()
    client = app.test_client()
    response = client.get('/api/system6/proof/revenue-recovery')

    assert response.status_code == 200
    data = response.get_json()
    assert data['domain'] == 'revenue_recovery'
    assert data['cases']['real_cases'] == 1
    assert data['cases']['synthetic_cases'] == 2
