"""API routes for LeakLock."""
from flask import Blueprint, request, redirect, send_file, jsonify
from werkzeug.utils import secure_filename
import uuid

from templates import page_upload, page_results, page_report
from services.scanner import scan_file
from services.cache import cache_get, cache_set
from models.db import get_pool

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
    """Run scan on sample CSV."""
    from services.scanner import scan_file
    from csv_scanner import save_scan_to_db
    
    # Read sample CSV
    with open('static/sample_data.csv', 'rb') as f:
        raw = f.read()
    
    # Run scan
    result = scan_file(raw)
    
    # Save to DB
    try:
        from config import DB_CONFIG
        save_scan_to_db(result, DB_CONFIG)
    except Exception as e:
        print(f'[WARN] Demo scan DB save failed: {e}')
    
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
    
    # Capture email
    email = request.form.get('email', '').strip()
    if email and '@' in email:
        try:
            from models.db import capture_email as db_capture_email
            db_capture_email(scan_id, email)
        except Exception as e:
            print(f'[WARN] Email capture failed: {e}')
    
    return redirect(f'/results/{result["scan_id"]}')
