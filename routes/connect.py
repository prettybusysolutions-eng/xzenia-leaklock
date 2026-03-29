"""OAuth connect routes for LeakLock platform integrations."""
import secrets
import logging
from datetime import datetime, timedelta, timezone
from flask import Blueprint, redirect, request, session
from connectors import CONNECTORS, PLATFORM_META
from connectors.base import encrypt_token, decrypt_token, normalize_to_scan_rows
from services.consequence import ingest_scan_result_to_consequence_cases

logger = logging.getLogger(__name__)
connect_bp = Blueprint('connect', __name__, url_prefix='/connect')


def save_connection(platform, email, access_token, refresh_token, expires_in, realm_id, account_name):
    """Save OAuth connection to DB."""
    from models.db import get_pool
    pool = get_pool()
    conn = pool.getconn()
    try:
        cur = conn.cursor()
        expires_at = None
        if expires_in:
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=int(expires_in))
        cur.execute(
            """
            INSERT INTO saas_connections (platform, user_email, access_token_enc, refresh_token_enc,
                token_expires_at, realm_id, account_name, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, 'active')
            ON CONFLICT (platform, user_email) DO UPDATE SET
                access_token_enc = EXCLUDED.access_token_enc,
                refresh_token_enc = EXCLUDED.refresh_token_enc,
                token_expires_at = EXCLUDED.token_expires_at,
                realm_id = EXCLUDED.realm_id,
                account_name = EXCLUDED.account_name,
                status = 'active',
                connected_at = NOW()
            RETURNING id::text
            """,
            (
                platform,
                email,
                encrypt_token(access_token),
                encrypt_token(refresh_token) if refresh_token else None,
                expires_at,
                realm_id,
                account_name,
            ),
        )
        row = cur.fetchone()
        conn.commit()
        return row[0] if row else None
    except Exception as e:
        logger.error(f'save_connection error: {e}')
        conn.rollback()
        raise
    finally:
        pool.putconn(conn)


def get_connection(platform, email):
    """Load and decrypt connection for a user."""
    from models.db import get_pool
    pool = get_pool()
    conn = pool.getconn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT access_token_enc, refresh_token_enc, token_expires_at, realm_id, account_name
            FROM saas_connections WHERE platform=%s AND user_email=%s AND status='active'
            """,
            (platform, email),
        )
        row = cur.fetchone()
        if not row:
            return None
        access_token = decrypt_token(row[0])
        refresh_token = decrypt_token(row[1]) if row[1] else None
        return {
            'access_token': access_token,
            'refresh_token': refresh_token,
            'expires_at': row[2],
            'realm_id': row[3],
            'account_name': row[4],
        }
    finally:
        pool.putconn(conn)


@connect_bp.route('/<platform>')
def start_oauth(platform):
    """Initiate OAuth flow for a platform."""
    if platform not in CONNECTORS:
        return '<h1>Unknown platform</h1>', 404

    connector = CONNECTORS[platform]()

    if not connector.is_configured():
        meta = PLATFORM_META.get(platform, {})
        return f"""<!DOCTYPE html>
<html>
<head><title>Connect {meta.get('name','')}</title>
<style>
body{{font-family:system-ui;background:#060d1b;color:#f1f5f9;display:flex;align-items:center;justify-content:center;min-height:100vh;margin:0}}
.card{{background:#0d1a2e;border:1px solid rgba(255,255,255,0.08);border-radius:20px;padding:48px;text-align:center;max-width:480px}}
h2{{font-size:24px;margin-bottom:12px}} p{{color:#94a3b8;margin-bottom:24px}}
a{{color:#38bdf8;text-decoration:none}}
</style></head>
<body><div class="card">
<div style="font-size:48px;margin-bottom:16px">{meta.get('icon','')}</div>
<h2>{meta.get('name','')} Integration</h2>
<p>This integration is configured but credentials are not set up yet.<br>Set <code>{platform.upper()}_CLIENT_ID</code> and <code>{platform.upper()}_CLIENT_SECRET</code> in your .env file.</p>
<p style="margin-top:24px"><a href="/upload">&larr; Back to upload</a></p>
</div></body></html>""", 503

    state = secrets.token_urlsafe(16)
    session['oauth_state'] = state
    session['oauth_platform'] = platform

    return redirect(connector.get_auth_url(state))


@connect_bp.route('/<platform>/callback')
def oauth_callback(platform):
    """Handle OAuth callback, exchange code for tokens, run scan."""
    if platform not in CONNECTORS:
        return '<h1>Unknown platform</h1>', 404

    error = request.args.get('error')
    if error:
        return f'<h1>Connection failed: {error}</h1><p><a href="/upload">Try again</a></p>', 400

    code = request.args.get('code', '')
    state = request.args.get('state', '')
    expected_state = session.get('oauth_state', '')
    if expected_state and state != expected_state:
        logger.warning(f'OAuth state mismatch for {platform}')

    connector = CONNECTORS[platform]()

    try:
        token_data = connector.exchange_code(code, state)
    except Exception as e:
        logger.error(f'Token exchange failed for {platform}: {e}')
        return f'<h1>Connection error</h1><p>{e}</p><p><a href="/upload">Try again</a></p>', 500

    user_email = session.get('user_email', f'user_{state[:8]}@connected')

    try:
        save_connection(
            platform=platform,
            email=user_email,
            access_token=token_data['access_token'],
            refresh_token=token_data.get('refresh_token', ''),
            expires_in=token_data.get('expires_in', 3600),
            realm_id=token_data.get('realm_id', ''),
            account_name=token_data.get('account_name', f'{platform.title()} Account'),
        )
    except Exception as e:
        logger.warning(f'Could not save connection (DB may not have table yet): {e}')

    try:
        transactions = connector.fetch_transactions(
            access_token=token_data['access_token'],
            realm_id=token_data.get('realm_id', ''),
            days_back=365,
        )

        if not transactions:
            return '<h1>Connected! No transactions found in last 12 months.</h1><p><a href="/upload">Upload a file instead</a></p>', 200

        rows = normalize_to_scan_rows(transactions)

        import io
        import csv
        output = io.StringIO()
        if rows:
            writer = csv.DictWriter(output, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
        raw_bytes = output.getvalue().encode()

        from csv_scanner import scan_csv, save_scan_to_db
        from config import DB_CONFIG
        from services.cache import cache_set

        result = scan_csv(raw_bytes)
        result['source'] = platform
        result['source_kind'] = 'connector_oauth'
        result['account_name'] = token_data.get('account_name', '')
        result['is_synthetic'] = False

        try:
            cache_set(result['scan_id'], result)
        except Exception:
            pass
        try:
            save_scan_to_db(result, DB_CONFIG)
        except Exception:
            pass
        try:
            ingest_scan_result_to_consequence_cases(
                result,
                source_system=platform,
                source_kind='connector_oauth',
                explicit_is_synthetic=False,
            )
        except Exception:
            pass

        return redirect(f'/results/{result["scan_id"]}')
    except Exception as e:
        logger.error(f'Scan after connect failed: {e}')
        import traceback
        traceback.print_exc()
        return f'<h1>Connected but scan failed</h1><p>{e}</p><p><a href="/upload">Upload manually instead</a></p>', 500


@connect_bp.route('/status')
def connection_status():
    """Show connected platforms for current user."""
    email = session.get('user_email', '')
    if not email:
        return redirect('/upload')

    from models.db import get_pool
    pool = get_pool()
    conn = pool.getconn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT platform, account_name, connected_at, last_sync_at, status
            FROM saas_connections WHERE user_email=%s ORDER BY connected_at DESC
            """,
            (email,),
        )
        connections = cur.fetchall()
    finally:
        pool.putconn(conn)

    return str(connections)
