# TASK-REPORT-SYSTEM6-002

## Scope
Build System 6 Layer 2 for `xzenia-saas` with real proof boundaries:
- canonical evidence schema
- operator proof report
- synthetic/demo exclusion handling
- first intake path from scan results into consequence cases
- verification notes

## What changed

### 1) Canonical evidence schema
Added `services/consequence.py` with:
- `REVENUE_RECOVERY_REQUIRED_EVIDENCE_FIELDS`
- `validate_revenue_recovery_evidence(payload)`
- `build_revenue_recovery_evidence(...)`
- `infer_synthetic_flag(...)`
- `ingest_scan_result_to_consequence_cases(...)`

The schema requires:
- domain identity
- scan/source identifiers
- anomaly type
- detection timestamp
- conservative estimated impact metadata
- concrete evidence items
- explicit `is_synthetic`

Important truth boundary:
- estimated impact is stored as **scan evidence only**
- no realized business outcome is fabricated

### 2) Operator proof report
Added JSON proof report route:
- `GET /api/system6/proof/revenue-recovery`

Added DB helper:
- `models.db.get_proof_report(domain='revenue_recovery')`

The report explicitly separates:
- real cases
- synthetic/demo cases
- real-only proof metrics
- excluded synthetic/demo counts

### 3) Synthetic/demo handling
Explicit synthetic tagging added to demo/sample path:
- `routes/api.py:/demo`
  - marks scan result with `source='demo_sample_csv'`
  - marks `source_kind='demo_sample'`
  - sets `is_synthetic=True`
  - consequence intake uses `explicit_is_synthetic=True`

Comments were added near the code to explain that demo/sample/test paths remain visible for operator awareness but are excluded from proof metrics.

### 4) First intake path
Wired scan-result intake into consequence cases for real scan flows:
- uploaded file scans (`routes/api.py`)
- direct Stripe scans (`routes/stripe_scan.py`)
- OAuth connector scans (`routes/connect.py`)

Behavior:
- each detected leak pattern becomes one consequence case
- case evidence payload uses canonical revenue-recovery schema
- ingestion is idempotent by `source_event_id = {scan_id}:{anomaly_type}`
- non-demo paths use `synthetic=false`
- demo/sample paths use `synthetic=true`

### 5) Exports
Updated package exports so the new proof and consequence helpers are accessible through:
- `services/__init__.py`
- `models/__init__.py`

### 6) Tests
Added `tests/test_system6.py` covering:
- evidence validator with example payload
- intake path creation for a real case
- synthetic inference for demo/sample path
- app boot + proof report route JSON

## Verification performed

### App boots
Verified via test creating Flask app through `create_app()`.

### Proof report route works
Verified via Flask test client request to:
- `/api/system6/proof/revenue-recovery`

### Evidence validator works
Verified via example payload built from a scan result and leak pattern.

### Test command
```bash
pytest tests/test_system6.py tests/test_scanner.py
```

## What remains open
- Proof report currently returns aggregate JSON only; there is no operator UI yet.
- Realized business outcomes still depend on later human-approved execution + outcome recording.
- Historical backfill of older demo/sample-derived consequence rows is still open if any were already created before this change.
- Upload path treats manual uploads as real unless they come through an explicit demo/sample route. That is honest, but it cannot detect a user manually re-uploading the sample file without additional file fingerprinting.

## Honest status
System 6 Layer 2 is now materially wired:
- evidence schema exists
- proof report exists
- demo/sample exclusion is explicit
- detected scans can now create consequence case records

But this is **not** full proof of autonomous revenue recovery. It is proof infrastructure plus first intake. Real proof still requires real cases, real approved actions, and real measured outcomes.
