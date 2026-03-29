"""API routes for LeakLock."""
from flask import Blueprint, request, redirect, send_file, jsonify
from werkzeug.utils import secure_filename
import uuid

from templates import page_upload, page_results, page_report
from services.scanner import scan_file
from services.cache import cache_get, cache_set
from services.consequence import ingest_scan_result_to_consequence_cases, is_sample_csv_upload
from models.db import (
    get_pool,
    get_proof_report,
    get_consequence_action,
    get_case_actions,
    record_action_decision,
    record_action_execution,
    record_action_outcome,
)

api_bp = Blueprint('api', __name__, url_prefix='')


def get_scan_by_id(scan_id):
    """Fetch scan from cache or DB."""
    if len(scan_id) < 8:
        return None
    
    try:
        scan = cache_get(f"scan_{scan_id}")
    except Exception:
        scan = None
    
    if not scan:
        # Fall back to DB reconstruction
        from models.db import get_scan_leaks_from_db
        try:
            db_leaks = get_scan_leaks_from_db(scan_id)
            if db_leaks:
                total_leakage = sum(l.get('amount_estimate', 0) for l in db_leaks)
                for l in db_leaks:
                    if l.get('details') and isinstance(l['details'], dict):
                        l['pattern_name'] = l['details'].get('pattern_name', l.get('pattern', '').replace('_', ' ').title())
                        l['description'] = l['details'].get('description', '')
                        l['affected_rows'] = l['details'].get('affected_rows', 0)
                scan = {
                    'scan_id': scan_id,
                    'rows_parsed': sum(l.get('affected_rows', 1) for l in db_leaks),
                    'total_revenue': total_leakage,
                    'total_leakage': total_leakage,
                    'patterns_triggered': len(db_leaks),
                    'leaks': db_leaks,
                    'column_mapping': {}
                }
        except Exception:
            pass
    
    return scan


def get_customer_dashboard(customer_id):
    """Get legacy dashboard for customer."""
    from models.db import get_customer_with_token, get_detected_leaks
    from templates import page_legacy_dashboard, _demo_dashboard
    
    token = request.args.get('token', '')
    try:
        customer = get_customer_with_token(customer_id, token)
        if customer:
            leaks = get_detected_leaks(customer_id)
            return page_legacy_dashboard(customer, leaks)
        else:
            return _demo_dashboard(customer_id)
    except Exception as e:
        return f'<h1>Error</h1><pre>{e}</pre>', 500


def validate_upload(file):
    """Validate uploaded file."""
    from config import MAX_FILE_SIZE, ALLOWED_EXTENSIONS, ALLOWED_MIME_TYPES
    import magic
    
    # Size check
    file.seek(0, 2)
    size = file.tell()
    file.seek(0)
    if size > MAX_FILE_SIZE:
        return None, "File too large (max 100MB)."
    
    # Extension check
    filename = secure_filename(file.filename)
    if not filename:
        return None, "Please select a file."
    ext = '.' + filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    if ext not in ALLOWED_EXTENSIONS:
        return None, f"File type '{ext}' not accepted."
    
    # Empty file check
    if size == 0:
        return None, "The uploaded file is empty."
    
    # MIME type check
    header = file.read(2048)
    file.seek(0)
    try:
        mime = magic.from_buffer(header, mime=True)
        if mime not in ALLOWED_MIME_TYPES:
            return None, f"Invalid file type: {mime}"
    except Exception:
        pass
    
    return filename, None


@api_bp.route('/demo')
def demo_scan():
    """Run scan on sample CSV.

    Synthetic boundary:
    demo/sample-derived consequence cases are marked synthetic=True so they are
    visible for demos but excluded from System 6 proof metrics.
    """
    from services.scanner import scan_file
    from csv_scanner import save_scan_to_db

    # Read sample CSV
    with open('static/sample_data.csv', 'rb') as f:
        raw = f.read()

    # Run scan
    result = scan_file(raw)
    result['source'] = 'demo_sample_csv'
    result['source_kind'] = 'demo_sample'
    result['is_synthetic'] = True

    # Save to DB
    try:
        from config import DB_CONFIG
        save_scan_to_db(result, DB_CONFIG)
    except Exception as e:
        print(f'[WARN] Demo scan DB save failed: {e}')

    try:
        ingest_scan_result_to_consequence_cases(
            result,
            source_system='demo_sample_csv',
            source_kind='demo_sample',
            explicit_is_synthetic=True,
        )
    except Exception as e:
        print(f'[WARN] Demo consequence intake failed: {e}')

    # Save to cache
    try:
        cache_set(f"scan_{result['scan_id']}", result)
    except Exception as e:
        print(f'[WARN] Demo scan cache set failed: {e}')

    return redirect(f"/results/{result['scan_id']}")


@api_bp.route('/sample')
def sample_csv():
    """Serve sample CSV."""
    return send_file('static/sample_data.csv', as_attachment=True, download_name='leaklock_sample.csv')


def _json_required_payload():
    payload = request.get_json(silent=True) or {}
    if not isinstance(payload, dict):
        return {}
    return payload


def _extract_actor_fields(payload):
    actor = payload.get('actor')
    actor_id = payload.get('actor_id')
    actor_type = payload.get('actor_type')
    return actor, actor_id, actor_type


def _extract_verification(payload):
    verification = payload.get('verification')
    if verification is None:
        return None
    return verification


@api_bp.route('/api/system6/actions/<action_id>')
def system6_get_action(action_id):
    """Return one action lifecycle record."""
    action = get_consequence_action(action_id)
    if not action:
        return jsonify({'error': 'action_not_found'}), 404
    return jsonify(action)


@api_bp.route('/api/system6/cases/<case_id>/actions')
def system6_get_case_actions(case_id):
    """Return all lifecycle actions for a case."""
    return jsonify({'case_id': case_id, 'actions': get_case_actions(case_id)})


@api_bp.route('/api/system6/actions/<action_id>/decision', methods=['POST'])
def system6_action_decision(action_id):
    """Approve or reject a pending consequence action with bound actor metadata."""
    payload = _json_required_payload()
    approval_status = str(payload.get('approval_status', '')).strip().lower()
    actor, actor_id, actor_type = _extract_actor_fields(payload)
    notes = payload.get('notes')

    try:
        action = record_action_decision(
            action_id,
            approval_status=approval_status,
            approved_by=actor if isinstance(actor, str) else None,
            decision_notes=notes,
            actor=actor,
            actor_id=actor_id,
            actor_type=actor_type,
        )
    except ValueError as exc:
        return jsonify({'error': 'invalid_action_decision', 'detail': str(exc)}), 400

    return jsonify({'ok': True, 'action': action})


@api_bp.route('/api/system6/actions/<action_id>/execution', methods=['POST'])
def system6_action_execution(action_id):
    """Record execution state for an approved consequence action."""
    payload = _json_required_payload()
    execution_status = str(payload.get('execution_status', '')).strip().lower()
    actor, actor_id, actor_type = _extract_actor_fields(payload)
    notes = payload.get('notes')
    verification = _extract_verification(payload)

    try:
        action = record_action_execution(
            action_id,
            execution_status=execution_status,
            execution_notes=notes,
            execution_actor=actor if isinstance(actor, str) else None,
            actor=actor,
            actor_id=actor_id,
            actor_type=actor_type,
            verification=verification,
        )
    except ValueError as exc:
        return jsonify({'error': 'invalid_action_execution', 'detail': str(exc)}), 400

    return jsonify({'ok': True, 'action': action})


@api_bp.route('/api/system6/actions/<action_id>/outcome', methods=['POST'])
def system6_action_outcome(action_id):
    """Record measured outcome for an executed consequence action."""
    payload = _json_required_payload()
    outcome_type = str(payload.get('outcome_type', '')).strip()
    outcome_value = payload.get('outcome_value')
    outcome_notes = payload.get('outcome_notes')
    outcome_currency = str(payload.get('outcome_currency', 'USD')).strip() or 'USD'
    actor, actor_id, actor_type = _extract_actor_fields(payload)
    outcome_evidence = payload.get('outcome_evidence')
    verification = _extract_verification(payload)

    try:
        action = record_action_outcome(
            action_id,
            outcome_type=outcome_type,
            outcome_value=outcome_value,
            outcome_notes=outcome_notes,
            outcome_currency=outcome_currency,
            actor=actor,
            actor_id=actor_id,
            actor_type=actor_type,
            outcome_evidence=outcome_evidence,
            verification=verification,
        )
    except ValueError as exc:
        return jsonify({'error': 'invalid_action_outcome', 'detail': str(exc)}), 400

    return jsonify({'ok': True, 'action': action})


@api_bp.route('/api/system6/proof/revenue-recovery')
def system6_proof_revenue_recovery():
    """Operator proof report for System 6 / revenue recovery.

    Proof is restricted to non-synthetic cases. Demo/sample/test cases remain visible
    for operator awareness, but they do not count as proof of consequence.
    """
    return jsonify(get_proof_report('revenue_recovery'))


@api_bp.route('/ops/system6/proof/revenue-recovery')
def system6_proof_revenue_recovery_page():
    """Simple operator-facing proof page for System 6."""
    report = get_proof_report('revenue_recovery')
    proof = report.get('proof_metrics', {})
    recent_cases = report.get('recent_cases', [])
    recent_actions = report.get('recent_actions', [])

    case_rows = []
    for case in recent_cases:
        badge = 'synthetic' if case.get('is_synthetic') else 'real'
        case_rows.append(
            f"<tr>"
            f"<td style='padding:10px;border-bottom:1px solid #1e293b'>{case.get('detected_at','')}</td>"
            f"<td style='padding:10px;border-bottom:1px solid #1e293b'>{case.get('anomaly_type','')}</td>"
            f"<td style='padding:10px;border-bottom:1px solid #1e293b'>{case.get('source_system','')}</td>"
            f"<td style='padding:10px;border-bottom:1px solid #1e293b'>{badge}</td>"
            f"<td style='padding:10px;border-bottom:1px solid #1e293b'>{case.get('pending_actions',0)}</td>"
            f"<td style='padding:10px;border-bottom:1px solid #1e293b'>{case.get('approved_actions',0)}</td>"
            f"<td style='padding:10px;border-bottom:1px solid #1e293b'>{case.get('executed_actions',0)}</td>"
            f"<td style='padding:10px;border-bottom:1px solid #1e293b'>{case.get('measured_outcomes',0)}</td>"
            f"<td style='padding:10px;border-bottom:1px solid #1e293b'>{case.get('evidenced_outcomes',0)}</td>"
            f"<td style='padding:10px;border-bottom:1px solid #1e293b'>{case.get('execution_verified_actions',0)}/{case.get('outcome_verified_actions',0)}</td>"
            f"</tr>"
        )
    case_rows_html = ''.join(case_rows) or "<tr><td colspan='10' style='padding:10px;color:#94a3b8'>No consequence cases yet.</td></tr>"

    action_rows = []
    for action in recent_actions:
        badge = 'synthetic' if action.get('is_synthetic') else 'real'
        outcome_summary = action.get('outcome_type') or '—'
        if action.get('outcome_value') is not None:
            outcome_summary = f"{outcome_summary} (${action.get('outcome_value')})"
        evidence_summary = f"{action.get('outcome_evidence_count', 0)} ref(s)"
        verification_summary = f"exec={action.get('execution_verification_status','unverified')} · outcome={action.get('outcome_verification_status','unverified')}"
        actor_summary = action.get('decision_actor') or action.get('approved_by') or action.get('execution_actor') or '—'
        if action.get('decision_actor_is_legacy') or action.get('execution_actor_is_legacy') or action.get('outcome_actor_is_legacy'):
            actor_summary = f"{actor_summary} (legacy)"
        action_rows.append(
            f"<tr>"
            f"<td style='padding:10px;border-bottom:1px solid #1e293b'>{action.get('created_at','')}</td>"
            f"<td style='padding:10px;border-bottom:1px solid #1e293b'>{action.get('anomaly_type','')}</td>"
            f"<td style='padding:10px;border-bottom:1px solid #1e293b'>{badge}</td>"
            f"<td style='padding:10px;border-bottom:1px solid #1e293b'>{actor_summary}</td>"
            f"<td style='padding:10px;border-bottom:1px solid #1e293b'>{action.get('approval_status','')}</td>"
            f"<td style='padding:10px;border-bottom:1px solid #1e293b'>{action.get('execution_status','')}</td>"
            f"<td style='padding:10px;border-bottom:1px solid #1e293b'>{verification_summary}</td>"
            f"<td style='padding:10px;border-bottom:1px solid #1e293b'>{outcome_summary}</td>"
            f"<td style='padding:10px;border-bottom:1px solid #1e293b'>{evidence_summary}</td>"
            f"<td style='padding:10px;border-bottom:1px solid #1e293b'><a href=\"/api/system6/actions/{action.get('action_id','')}\">inspect</a></td>"
            f"</tr>"
        )
    action_rows_html = ''.join(action_rows) or "<tr><td colspan='10' style='padding:10px;color:#94a3b8'>No lifecycle actions yet.</td></tr>"

    html = f"""<!DOCTYPE html>
<html lang='en'>
<head>
<meta charset='utf-8'>
<meta name='viewport' content='width=device-width, initial-scale=1'>
<title>System 6 Proof — Revenue Recovery</title>
<style>
body{{font-family:Inter,-apple-system,sans-serif;background:#020617;color:#e2e8f0;padding:32px}}
.card{{background:#0f172a;border:1px solid #1e293b;border-radius:16px;padding:20px;margin-bottom:20px}}
h1,h2{{margin:0 0 12px 0}} small, p{{color:#94a3b8}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px}}
.metric{{background:#111827;border:1px solid #1f2937;border-radius:12px;padding:14px}}
.value{{font-size:28px;font-weight:700;margin-top:6px}}
table{{width:100%;border-collapse:collapse}}
a{{color:#38bdf8}}
.code{{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:12px;color:#cbd5e1}}
</style>
</head>
<body>
  <h1>System 6 Proof — Revenue Recovery</h1>
  <p>Proof boundary: only <strong>non-synthetic</strong> consequence cases count as proof.</p>
  <div class='grid'>
    <div class='metric'><small>Real cases</small><div class='value'>{report.get('cases',{}).get('real_cases',0)}</div></div>
    <div class='metric'><small>Synthetic cases</small><div class='value'>{report.get('cases',{}).get('synthetic_cases',0)}</div></div>
    <div class='metric'><small>Recommended actions</small><div class='value'>{proof.get('recommended_actions',0)}</div></div>
    <div class='metric'><small>Approved actions</small><div class='value'>{proof.get('approved_actions',0)}</div></div>
    <div class='metric'><small>Executed actions</small><div class='value'>{proof.get('executed_actions',0)}</div></div>
    <div class='metric'><small>Measured outcomes</small><div class='value'>{proof.get('measured_outcomes',0)}</div></div>
    <div class='metric'><small>Evidenced outcomes</small><div class='value'>{report.get('actions',{}).get('real_evidenced_outcomes',0)}</div></div>
    <div class='metric'><small>Execution verified</small><div class='value'>{report.get('actions',{}).get('real_execution_verified_actions',0)}</div></div>
    <div class='metric'><small>Outcome verified</small><div class='value'>{report.get('actions',{}).get('real_outcome_verified_actions',0)}</div></div>
    <div class='metric'><small>Realized value</small><div class='value'>${proof.get('realized_value',0)}</div></div>
  </div>
  <div class='card'>
    <h2>Recent consequence cases</h2>
    <table>
      <thead><tr><th align='left'>Detected</th><th align='left'>Anomaly</th><th align='left'>Source</th><th align='left'>Class</th><th align='left'>Pending</th><th align='left'>Approved</th><th align='left'>Executed</th><th align='left'>Measured</th><th align='left'>Evidenced</th><th align='left'>Verified E/O</th></tr></thead>
      <tbody>{case_rows_html}</tbody>
    </table>
  </div>
  <div class='card'>
    <h2>Action lifecycle</h2>
    <p class='code'>Inspect JSON: /api/system6/actions/&lt;action_id&gt; · /api/system6/cases/&lt;case_id&gt;/actions</p>
    <table>
      <thead><tr><th align='left'>Created</th><th align='left'>Anomaly</th><th align='left'>Class</th><th align='left'>Actor</th><th align='left'>Approval</th><th align='left'>Execution</th><th align='left'>Verification</th><th align='left'>Outcome</th><th align='left'>Evidence</th><th align='left'>Inspect</th></tr></thead>
      <tbody>{action_rows_html}</tbody>
    </table>
  </div>
  <div class='card'>
    <h2>Raw proof JSON</h2>
    <p><a href='/api/system6/proof/revenue-recovery'>View JSON report</a></p>
  </div>
</body>
</html>"""
    return html


@api_bp.route('/report/<scan_id>')
def report(scan_id):
    """Printable PDF report."""
    scan = get_scan_by_id(scan_id)
    if not scan:
        return '<h1>Report not found</h1><p><a href="/upload">Run a new scan</a></p>', 404
    return page_report(scan)


@api_bp.route('/api/save-results', methods=['POST'])
def save_results():
    """Save scan results + capture email via POST form."""
    from models.db import capture_email as db_capture_email

    email = request.form.get('email', '').strip()
    scan_id = request.form.get('scan_id', '').strip()

    if not scan_id:
        return '<div style="color:#f87171;">No scan ID provided.</div>', 400

    if email and '@' in email:
        try:
            db_capture_email(scan_id, email)
        except Exception as e:
            print(f'[WARN] save-results email capture failed: {e}')
        return f'<div style="background:#dcfce7;padding:16px;border-radius:8px;text-align:center;">&#x2705; <strong>Saved!</strong> Report sent to {email}. <a href="/report/{scan_id}" target="_blank" style="color:#059669;font-weight:600;">View PDF &rarr;</a></div>'
    return '<div style="background:#fee2e2;padding:16px;border-radius:8px;text-align:center;">&#x274C; Invalid email address</div>'


@api_bp.route('/capture_email/<scan_id>', methods=['POST'])
def capture_email(scan_id):
    """Capture email for scan results."""
    from models.db import capture_email as db_capture_email
    
    email = request.form.get('email', '').strip()
    if email and '@' in email:
        try:
            db_capture_email(scan_id, email)
        except Exception as e:
            print(f'[WARN] Email capture failed: {e}')
        return f'<div style="background:#dcfce7;padding:16px;border-radius:8px;text-align:center;">&#x2705; <strong>Email captured!</strong> Your report has been sent to {email}. <a href="/report/{scan_id}" target="_blank" style="color:#059669;font-weight:600;">View PDF Report &rarr;</a></div>'
    return '<div style="background:#fee2e2;padding:16px;border-radius:8px;text-align:center;">&#x274C; Invalid email address</div>'


def handle_upload():
    """Handle file upload POST."""
    from csv_scanner import scan_csv, save_scan_to_db
    from config import DB_CONFIG
    
    # Support multiple files
    uploaded_files = request.files.getlist('files')
    if not uploaded_files or all(f.filename == '' for f in uploaded_files):
        uploaded_files = [request.files.get('csvfile')]
    
    if not uploaded_files or not uploaded_files[0] or uploaded_files[0].filename == '':
        return page_upload(error='No file was uploaded.'), 400
    
    # Process files
    combined_rows = 0
    combined_revenue = 0.0
    combined_leaks = {}
    last_col_map = {}
    scan_id = str(uuid.uuid4())
    errors = []
    any_sample_upload = False
    raw_payloads = []
    
    for uploaded_file in uploaded_files:
        if not uploaded_file or uploaded_file.filename == '':
            continue
        
        filename, err = validate_upload(uploaded_file)
        if err:
            return page_upload(error=err), 400
        
        try:
            raw_bytes = uploaded_file.read()
            if len(raw_bytes) == 0:
                errors.append(f"File {uploaded_file.filename} is empty.")
                continue

            file_is_sample = is_sample_csv_upload(raw_bytes)
            any_sample_upload = any_sample_upload or file_is_sample
            raw_payloads.append(raw_bytes)

            result = scan_csv(raw_bytes)
            
            if result.get('error'):
                errors.append(f"{uploaded_file.filename}: {result['error']}")
                continue
            
            combined_rows += result.get('rows_parsed', 0)
            combined_revenue += result.get('total_revenue', 0)
            last_col_map = result.get('column_mapping', {})
            
            # Merge leaks
            for leak in result.get('leaks', []):
                pname = leak.get('pattern_name', '')
                if pname not in combined_leaks or leak.get('amount_estimate', 0) > combined_leaks[pname].get('amount_estimate', 0):
                    combined_leaks[pname] = leak
        except Exception as e:
            errors.append(f"Error processing {uploaded_file.filename}: {str(e)}")
            print(f'[ERROR] File scan error: {e}')
    
    if combined_rows == 0:
        return page_upload(error='No valid data found in uploaded files.'), 400
    
    # Build combined result
    final_leaks = sorted(combined_leaks.values(), key=lambda x: x.get('amount_estimate', 0), reverse=True)
    total_leakage = sum(l.get('amount_estimate', 0) for l in final_leaks)
    
    result = {
        'scan_id': scan_id,
        'rows_parsed': combined_rows,
        'total_revenue': round(combined_revenue, 2),
        'total_leakage': round(total_leakage, 2),
        'patterns_triggered': len(final_leaks),
        'leaks': final_leaks,
        'column_mapping': last_col_map,
        'source': 'file_upload',
        'source_kind': 'file_upload',
        # Uploaded files are treated as real operator evidence unless they match
        # the shipped sample CSV fingerprint or come through an explicit demo path.
        'is_synthetic': any_sample_upload,
    }
    
    # Save to cache
    try:
        cache_set(result['scan_id'], result)
    except Exception as e:
        print(f'[WARN] Cache set failed: {e}')
    
    # Save to DB
    try:
        save_scan_to_db(result, DB_CONFIG)
    except Exception as e:
        print(f'[WARN] DB save failed: {e}')

    # First concrete System 6 intake path: scan results become consequence cases
    # with canonical evidence payloads. This does not fabricate outcomes; it only
    # records detected anomalies plus their supporting scan evidence.
    try:
        ingest_scan_result_to_consequence_cases(
            result,
            source_system='file_upload',
            source_kind='file_upload',
            explicit_is_synthetic=any_sample_upload,
            raw_bytes=raw_payloads[0] if len(raw_payloads) == 1 else None,
        )
    except Exception as e:
        print(f'[WARN] Consequence intake failed: {e}')
    
    # Capture email
    email = request.form.get('email', '').strip()
    if email and '@' in email:
        try:
            from models.db import capture_email as db_capture_email
            db_capture_email(scan_id, email)
        except Exception as e:
            print(f'[WARN] Email capture failed: {e}')
    
    return redirect(f'/results/{result["scan_id"]}')
