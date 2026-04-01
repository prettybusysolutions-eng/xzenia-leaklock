# LeakLock — Enterprise CSV Data Leak Detection

> **"Your CSV data is leaking. Find out who's exfiltrating it — before they do."**

---

## What It Is

LeakLock is a production-grade SaaS platform that detects and attributes data exfiltration within CSV file processing. It instruments every CSV operation — uploads, field access patterns, query execution, and download attempts — and constructs a forensic audit trail that pins liability to specific users, sessions, and data fields.

**Not a DLP wrapper. Not a SIEM module. A purpose-built forensic instrument for structured data environments.**

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    CLIENT UPLOAD                         │
│         CSV File + Authenticated Session                  │
└────────────────────────┬────────────────────────────────┘
                         │ POST /upload
                         ▼
┌─────────────────────────────────────────────────────────┐
│                  LEAKLOCK API                            │
│   FastAPI + PostgreSQL + Stripe                          │
│                                                          │
│   ┌──────────┐  ┌───────────┐  ┌────────────┐           │
│   │ Upload   │  │ Field     │  │ Anomaly    │           │
│   │ + Hash   │  │ Access    │  │ Detection  │           │
│   │          │  │ Tracking  │  │            │           │
│   └──────────┘  └───────────┘  └────────────┘           │
│                                                          │
│   ┌──────────────────────────────────────────┐           │
│   │         FORENSIC AUDIT LOG                │           │
│   │   user · session · field · timestamp      │           │
│   └──────────────────────────────────────────┘           │
│                                                          │
│   ┌──────────────────────────────────────────┐           │
│   │       STRIPE PAYMENT WEBHOOK             │           │
│   │   Checkout.session.completed → activate   │           │
│   └──────────────────────────────────────────┘           │
└────────────────────────┬────────────────────────────────┘
                         │ notification
                         ▼
┌─────────────────────────────────────────────────────────┐
│               ADMIN DASHBOARD                            │
│   Forensic report · User timeline · Field heatmap         │
└─────────────────────────────────────────────────────────┘
```

---

## Quick Start

### Prerequisites
- Python 3.11+
- PostgreSQL 14+
- Stripe account (test mode by default; live mode when ready)
- SMTP provider (Resend, SendGrid, or any SMTP relay)

### Local Development

```bash
# 1. Clone
git clone https://github.com/prettybusysolutions-eng/xzenia-leaklock
cd xzenia-leaklock

# 2. Install
pip install -r requirements.txt

# 3. Configure
cp .env.example .env
# Edit .env with your Stripe keys and SMTP settings

# 4. Initialize database
export DATABASE_URL=postgresql://postgres:password@localhost:5432/leaklock
python -c "from models.db import init_db; init_db()"

# 5. Run
python -m uvicorn app:app --reload --port 8000
```

### Production Deployment (Render)

```bash
# 1. Create PostgreSQL
render.com → New → PostgreSQL → name: leaklock-db → Create

# 2. Connect GitHub repo
render.com → New → Web Service → connect prettybusysolutions-eng/xzenia-leaklock

# 3. Set environment variables
DATABASE_URL=postgresql://...     # from step 1
STRIPE_SECRET_KEY=sk_live_...     # Stripe live key
STRIPE_WEBHOOK_SECRET=whsec_...   # from Stripe Dashboard
LEAKLOCK_DOMAIN=https://your-url.onrender.com
SMTP_HOST=smtp.resend.dev
SMTP_PORT=587
SMTP_USER=resend
SMTP_PASS=re_xxx
SMTP_FROM=LeakLock <hello@yourdomain.com>

# 4. Deploy
# Note your URL, e.g. https://leaklock.onrender.com

# 5. Register Stripe webhook
# Stripe Dashboard → Developers → Webhooks →
# Add endpoint: https://leaklock.onrender.com/webhook/stripe
# Events: checkout.session.completed
```

---

## Core API Reference

### Endpoints

#### `POST /upload`
Upload a CSV file for scanning. Requires authentication.

```bash
curl -X POST https://leaklock.onrender.com/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@data.csv"
```

Response:
```json
{
  "scan_id": "uuid",
  "filename": "data.csv",
  "row_count": 15420,
  "column_count": 18,
  "file_hash": "sha256:abc123...",
  "processed_at": "2026-04-01T14:00:00Z",
  "result_url": "https://leaklock.onrender.com/scan/uuid"
}
```

#### `GET /scan/{scan_id}`
Retrieve forensic report for a scan.

```json
{
  "scan_id": "uuid",
  "filename": "data.csv",
  "processed_at": "2026-04-01T14:00:00Z",
  "payment_status": "completed",
  "columns": ["email", "ssn", "credit_card", "phone", ...],
  "leak_score": 0.73,
  "severity": "high",
  "findings": [
    {
      "field": "ssn",
      "exposure_count": 421,
      "severity": "critical",
      "recommendation": "Remove SSN from CSV or encrypt at rest"
    }
  ]
}
```

#### `POST /checkout/create`
Create a Stripe Checkout session for one-time scan payment.

```json
POST /checkout/create
{
  "scan_id": "uuid"
}
```

Response:
```json
{
  "session_id": "cs_xxx",
  "url": "https://checkout.stripe.com/c/pay/cs_xxx"
}
```

#### `POST /webhook/stripe`
Stripe webhook endpoint. Receives `checkout.session.completed` and activates the scan result.

---

## Payment Flow

```
1. User uploads CSV
2. LeakLock returns scan_id with payment_required=true
3. User initiates checkout → Stripe Checkout session created
4. User pays on Stripe
5. Stripe sends webhook: checkout.session.completed
6. LeakLock webhook handler verifies signature, activates scan result
7. User retrieves full forensic report at GET /scan/{scan_id}
8. Confirmation email sent to user
```

---

## Data Model

### Scan
| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Primary key |
| `filename` | String(255) | Uploaded filename |
| `row_count` | Integer | Number of rows |
| `column_count` | Integer | Number of columns |
| `file_hash` | String(64) | SHA-256 of file |
| `user_id` | String(100) | Uploader identifier |
| `payment_status` | Enum | pending / completed / failed |
| `stripe_session_id` | String(255) | Stripe Checkout session |
| `result` | JSON | Forensic findings |
| `created_at` | DateTime | Upload time |

### WebhookEvent
| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Primary key |
| `stripe_event_id` | String(255) | Stripe event ID (idempotency key) |
| `event_type` | String(100) | Stripe event type |
| `payload` | JSON | Raw event payload |
| `processed` | Boolean | Handled successfully |
| `processed_at` | DateTime | When handled |
| `error` | Text | Error message if failed |

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Yes | PostgreSQL connection string |
| `STRIPE_SECRET_KEY` | Yes (prod) | `sk_live_...` |
| `STRIPE_WEBHOOK_SECRET` | Yes (prod) | `whsec_...` |
| `LEAKLOCK_DOMAIN` | Yes (prod) | Public URL, e.g. `https://leaklock.onrender.com` |
| `SMTP_HOST` | Yes (prod) | SMTP server hostname |
| `SMTP_PORT` | Yes (prod) | SMTP port (587) |
| `SMTP_USER` | Yes (prod) | SMTP username |
| `SMTP_PASS` | Yes (prod) | SMTP password |
| `SMTP_FROM` | Yes (prod) | From address |

---

## Production Requirements

### Phase 1: Security (Required Before Live Payments)
- [ ] **Stripe Webhook Signature Verification**: Verify every webhook against `STRIPE_WEBHOOK_SECRET`. Reject all unsigned events. Current implementation may not verify signatures.
- [ ] **File Upload Size Limits**: Enforce maximum upload size (e.g., 50MB). Prevent DoS via large file uploads.
- [ ] **File Type Validation**: Verify uploaded files are valid CSV before processing. Reject any file that can't be parsed.
- [ ] **Authentication**: All scan endpoints require valid authentication tokens. No unauthenticated access to scan results.
- [ ] **SQL Injection**: All queries use parameterized statements. No raw string interpolation.

### Phase 2: Reliability (Required Before Production Traffic)
- [ ] **Webhook Dead Letter Queue**: Failed webhook processing retries with exponential backoff. Events that fail after 5 retries stored in DLQ for manual review.
- [ ] **Stripe Idempotency**: Use `Stripe-Enpoc-Key` on all Stripe API calls to prevent duplicate charges on retry.
- [ ] **Database Transactions**: Wrap scan creation + Stripe session creation in transactions. Roll back on partial failure.
- [ ] **File Storage**: Currently files processed in memory. Production requires object storage (S3, GCS, or Render Disk) with signed URLs.
- [ ] **Scan Result Caching**: Cache completed scan results in Redis. Avoid recomputing on repeated lookups.

### Phase 3: Observability (Required Before Incident Response)
- [ ] **Structured Logging**: JSON logs with scan_id, user_id, file_hash, duration_ms.
- [ ] **Scan Metrics**: Prometheus metrics — scan count, payment conversion rate, average scan time, leak detection rate by severity.
- [ ] **Webhook Metrics**: Track webhook receipt rate, processing latency, failure rate.
- [ ] **Alerting**: Alert on webhook failure rate >5%, payment spike or drop异常, scan queue depth >100.
- [ ] **Audit Log**: Immutable log of all payment state changes.

### Phase 4: Scalability
- [ ] **Async Scan Processing**: Currently synchronous. Move scan processing to background job queue (Celery + Redis, or Render Background Workers).
- [ ] **File Scanning Worker Pool**: Multiple workers process scans in parallel. Queue-based load balancing.
- [ ] **Database Indexes**: Add indexes on `scan.user_id`, `scan.stripe_session_id`, `scan.created_at`.
- [ ] **CDN**: Serve scan reports and static assets from CDN (Cloudflare).

### Phase 5: Business Logic
- [ ] **Subscription Model**: Add monthly/annual subscription option alongside one-time scan.
- [ ] **Bulk Pricing**: Enterprise pricing for high-volume scanning (50+ scans/month).
- [ ] **White Label**: Allow agencies to white-label with custom domain and branding.
- [ ] **Real-Time Field Monitoring**: Instead of post-upload scan, offer real-time field access monitoring as a separate product tier.

---

## Project Structure

```
xzenia-saas/
├── app.py                  # FastAPI application factory
├── config.py               # Environment variable parsing
├── models/
│   └── db.py               # SQLAlchemy models + init_db
├── routes/
│   ├── api.py              # Scan endpoints
│   ├── checkout.py         # Stripe Checkout
│   ├── pages.py            # Web UI pages
│   └── webhooks.py         # Stripe webhook handler
├── services/
│   ├── scanner.py          # CSV leak detection engine
│   ├── stripe_client.py    # Stripe API wrapper
│   ├── cache.py            # Caching layer
│   └── consequence.py      # Post-scan actions
├── connectors/
│   └── stripe_direct.py    # Direct Stripe connector
├── static/
│   └── sample_data.csv     # Sample CSV for testing
├── templates/
│   └── pages.py            # Jinja2 page templates
├── tests/
│   ├── test_scanner.py     # Scanner unit tests
│   └── test_system6.py     # Integration tests
├── .env.example            # Environment variable template
├── requirements.txt        # Python dependencies
├── render.yaml             # Render deployment config
├── Procfile               # Render process type
├── SPEC.md                # Full specification
└── README.md              # This file
```

---

## Glossary

| Term | Definition |
|------|------------|
| **Leak Score** | Composite score (0–1) of data exposure risk across all detected fields |
| **Forensic Report** | Complete breakdown of detected sensitive fields, exposure counts, and remediation guidance |
| **Webhook Idempotency** | Stripe events processed only once per event ID, preventing duplicate activations |
| **DLQ** | Dead Letter Queue — failed webhook events stored for manual review |

---

## License

Proprietary. © 2026 PrettyBusySolutions Engineering. All rights reserved.
