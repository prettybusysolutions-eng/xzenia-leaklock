"""System 6 consequence helpers for revenue-recovery proof.

Doctrine: build from truth, not performance.
Demo/sample-derived cases must be marked synthetic and excluded from proof.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any, Dict, List, Tuple

from models.db import create_consequence_case, add_consequence_action

REVENUE_RECOVERY_REQUIRED_EVIDENCE_FIELDS: Dict[str, Dict[str, Any]] = {
    'schema_version': {
        'type': str,
        'description': 'Canonical evidence schema version.',
    },
    'domain': {
        'type': str,
        'expected': 'revenue_recovery',
        'description': 'Consequence domain identifier.',
    },
    'scan_id': {
        'type': str,
        'description': 'Source scan identifier that produced the anomaly.',
    },
    'source_system': {
        'type': str,
        'description': 'Origin of the scan or transaction stream.',
    },
    'source_kind': {
        'type': str,
        'description': 'Kind of intake path, e.g. stripe_direct, connector_oauth, file_upload, demo_sample.',
    },
    'source_event_id': {
        'type': str,
        'description': 'Stable event identifier for idempotent case creation.',
    },
    'anomaly_type': {
        'type': str,
        'description': 'Canonical leak pattern name.',
    },
    'detected_at': {
        'type': str,
        'description': 'UTC ISO8601 detection timestamp.',
    },
    'estimated_impact': {
        'type': dict,
        'description': 'Conservative estimated impact from the scan; not claimed as realized outcome.',
    },
    'evidence_items': {
        'type': list,
        'description': 'Concrete evidence items supporting the case.',
    },
    'is_synthetic': {
        'type': bool,
        'description': 'True only for demo/sample-derived evidence.',
    },
}

_SAMPLE_CSV_PATH = Path(__file__).resolve().parent.parent / 'static' / 'sample_data.csv'
try:
    SAMPLE_CSV_SHA256 = sha256(_SAMPLE_CSV_PATH.read_bytes()).hexdigest()
except FileNotFoundError:
    SAMPLE_CSV_SHA256 = ''


def compute_content_sha256(raw_bytes: bytes) -> str:
    """Return a stable content fingerprint for uploaded bytes."""
    return sha256(raw_bytes or b'').hexdigest()


def is_sample_csv_upload(raw_bytes: bytes) -> bool:
    """True when uploaded bytes match the shipped sample CSV exactly."""
    if not SAMPLE_CSV_SHA256:
        return False
    return compute_content_sha256(raw_bytes) == SAMPLE_CSV_SHA256


def build_pending_recommendation(leak: Dict[str, Any]) -> Tuple[str, str]:
    """Generate a governed recommendation and causal hypothesis for a leak."""
    anomaly_type = str(leak.get('pattern') or leak.get('pattern_name', 'unknown')).strip()
    human_name = leak.get('pattern_name', anomaly_type.replace('_', ' ').title())
    how_to_fix = (leak.get('how_to_fix') or '').strip()
    description = (leak.get('description') or '').strip()

    recommendation = how_to_fix or f"Review and remediate detected pattern: {human_name}."
    causal_hypothesis = description or f"Detected anomaly suggests leakage pattern '{human_name}' is reducing realized revenue."
    return recommendation, causal_hypothesis


def _is_iso8601(value: str) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    try:
        datetime.fromisoformat(value.replace('Z', '+00:00'))
        return True
    except ValueError:
        return False


def validate_revenue_recovery_evidence(payload: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Validate a revenue-recovery evidence payload.

    Returns (is_valid, errors). Uses only stdlib so it works in constrained deploys.
    """
    errors: List[str] = []

    if not isinstance(payload, dict):
        return False, ['payload must be a dict']

    for field_name, spec in REVENUE_RECOVERY_REQUIRED_EVIDENCE_FIELDS.items():
        if field_name not in payload:
            errors.append(f'missing required field: {field_name}')
            continue
        if not isinstance(payload[field_name], spec['type']):
            errors.append(
                f"field {field_name} must be {spec['type'].__name__}, got {type(payload[field_name]).__name__}"
            )
            continue
        if spec.get('expected') is not None and payload[field_name] != spec['expected']:
            errors.append(f"field {field_name} must equal {spec['expected']!r}")

    if 'detected_at' in payload and not _is_iso8601(payload['detected_at']):
        errors.append('field detected_at must be ISO8601')

    estimated_impact = payload.get('estimated_impact')
    if isinstance(estimated_impact, dict):
        for key in ('amount', 'currency', 'basis'):
            if key not in estimated_impact:
                errors.append(f'estimated_impact missing required field: {key}')
        amount = estimated_impact.get('amount')
        if amount is not None and not isinstance(amount, (int, float)):
            errors.append('estimated_impact.amount must be numeric')

    evidence_items = payload.get('evidence_items')
    if isinstance(evidence_items, list):
        if not evidence_items:
            errors.append('evidence_items must contain at least one evidence item')
        for index, item in enumerate(evidence_items):
            if not isinstance(item, dict):
                errors.append(f'evidence_items[{index}] must be a dict')
                continue
            for required in ('kind', 'summary'):
                if not item.get(required):
                    errors.append(f'evidence_items[{index}] missing required field: {required}')

    return len(errors) == 0, errors


def build_revenue_recovery_evidence(
    *,
    scan_result: Dict[str, Any],
    leak: Dict[str, Any],
    source_system: str,
    source_kind: str,
    source_event_id: str,
    is_synthetic: bool,
    customer_ref: str | None = None,
) -> Dict[str, Any]:
    """Build canonical evidence for one revenue-recovery consequence case.

    Important truth boundary:
    - amount_estimate is only an estimate from scan evidence
    - no realized business outcome is claimed here
    """
    scan_id = str(scan_result.get('scan_id', ''))
    detected_at = scan_result.get('scanned_at') or datetime.now(timezone.utc).isoformat()
    anomaly_type = str(leak.get('pattern') or leak.get('pattern_name', 'unknown')).strip()
    description = leak.get('description') or ''

    evidence = {
        'schema_version': 'system6.revenue_recovery.v1',
        'domain': 'revenue_recovery',
        'scan_id': scan_id,
        'source_system': source_system,
        'source_kind': source_kind,
        'source_event_id': source_event_id,
        'anomaly_type': anomaly_type,
        'detected_at': detected_at,
        'estimated_impact': {
            'amount': float(leak.get('amount_estimate', 0) or 0),
            'currency': 'USD',
            'basis': 'scan_estimate_only_not_realized_outcome',
        },
        'evidence_items': [
            {
                'kind': 'scan_summary',
                'summary': description or f'Leak pattern detected: {anomaly_type}',
                'details': {
                    'pattern_name': leak.get('pattern_name', anomaly_type.replace('_', ' ').title()),
                    'severity': leak.get('severity'),
                    'confidence': leak.get('confidence'),
                    'affected_rows': leak.get('affected_rows', 0),
                    'scan_rows_parsed': scan_result.get('rows_parsed', 0),
                    'scan_total_revenue': scan_result.get('total_revenue', 0),
                    'scan_total_leakage': scan_result.get('total_leakage', 0),
                    'details': deepcopy(leak.get('details', {})),
                },
            }
        ],
        'is_synthetic': bool(is_synthetic),
    }

    if customer_ref:
        evidence['customer_ref'] = customer_ref

    return evidence


def infer_synthetic_flag(
    source_kind: str,
    explicit_flag: bool | None = None,
    raw_bytes: bytes | None = None,
) -> bool:
    """Infer whether a case must be synthetic.

    Demo/sample/test paths are synthetic by definition and must not count as proof.
    Exact sample CSV re-uploads are also synthetic via content fingerprint.
    """
    if explicit_flag is not None:
        return bool(explicit_flag)

    normalized = (source_kind or '').strip().lower()
    synthetic_markers = ('demo', 'sample', 'seed', 'synthetic', 'test')
    if any(marker in normalized for marker in synthetic_markers):
        return True

    if raw_bytes is not None and is_sample_csv_upload(raw_bytes):
        return True

    return False


def ingest_scan_result_to_consequence_cases(
    scan_result: Dict[str, Any],
    *,
    source_system: str,
    source_kind: str,
    explicit_is_synthetic: bool | None = None,
    customer_ref: str | None = None,
    raw_bytes: bytes | None = None,
    create_pending_actions: bool = True,
) -> List[Dict[str, Any]]:
    """Create/refresh consequence cases from a scan result.

    The first concrete intake path for System 6 is scan-result ingestion.
    It converts detected leak patterns into consequence cases with canonical evidence.
    """
    scan_id = str(scan_result.get('scan_id', '')).strip()
    if not scan_id:
        raise ValueError('scan_result is missing scan_id')

    leaks = scan_result.get('leaks') or []
    if not isinstance(leaks, list):
        raise ValueError('scan_result.leaks must be a list')

    is_synthetic = infer_synthetic_flag(source_kind, explicit_is_synthetic, raw_bytes=raw_bytes)
    created_cases: List[Dict[str, Any]] = []

    for leak in leaks:
        anomaly_type = str(leak.get('pattern') or leak.get('pattern_name', 'unknown')).strip()
        source_event_id = f'{scan_id}:{anomaly_type}'
        evidence = build_revenue_recovery_evidence(
            scan_result=scan_result,
            leak=leak,
            source_system=source_system,
            source_kind=source_kind,
            source_event_id=source_event_id,
            is_synthetic=is_synthetic,
            customer_ref=customer_ref,
        )
        is_valid, errors = validate_revenue_recovery_evidence(evidence)
        if not is_valid:
            raise ValueError(f'invalid evidence for {source_event_id}: {errors}')

        case_id = create_consequence_case(
            domain='revenue_recovery',
            source_system=source_system,
            source_event_id=source_event_id,
            anomaly_type=anomaly_type,
            evidence=evidence,
            scan_id=scan_id,
            customer_ref=customer_ref,
            is_synthetic=is_synthetic,
        )

        action_id = None
        if create_pending_actions and case_id:
            recommendation, causal_hypothesis = build_pending_recommendation(leak)
            action_id = add_consequence_action(
                case_id,
                recommendation=recommendation,
                causal_hypothesis=causal_hypothesis,
                requires_approval=True,
            )

        created_cases.append(
            {
                'case_id': case_id,
                'action_id': action_id,
                'source_event_id': source_event_id,
                'anomaly_type': anomaly_type,
                'is_synthetic': is_synthetic,
            }
        )

    return created_cases
