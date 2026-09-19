# Release diff and staging review — 2026-09-19

Status: release gate OPEN. This is an author-side engineering review, not independent third-party certification or proof of a production release.

Reviewed published PR #16 head `357a0e29a6dc83cedfafc71c60d33694a2da1dbb` and prepared the accompanying follow-up changes.

## Findings corrected

- Browser CSRF middleware rejected Stripe webhook requests. Exempt only the signature-authenticated webhook handler; retain CSRF on the administrative retry endpoint.
- The pinned Stripe 15 SDK returns objects without dictionary `.get`. Convert verified events using its public recursive dictionary API before processing.
- Processing failures acknowledged delivery with HTTP 200 even if persistence failed. Return 503 so provider retries remain possible.
- Unpaid completed checkout sessions were recorded as payments. Require paid status and support asynchronous payment success; tolerate absent customer details.
- Roll back failed payment writes before returning the database connection.
- Render now installs the tested dependency lock. Its encryption key must be supplied as a valid Fernet key rather than a generic generated string.

## Evidence

Local `.venv/bin/python -m pytest -q`: **48 passed**. `pip check`: no broken requirements. New checks use actual Stripe SDK verification of locally generated HMAC signatures, with CSRF enabled, and verify rejection of invalid signatures, retryable processing failure, retained administrative CSRF and no database access for unpaid checkout.

The signatures and checkout objects are synthetic. Payment persistence in these new checks is stubbed; no Stripe test-mode checkout or PostgreSQL-backed end-to-end purchase was completed.

## Staging gate remains open

No dedicated staging URL, PostgreSQL service or Stripe test credentials were available. Local PostgreSQL installation failed because the environment denied package-manager identity changes. No production deployment or payment was attempted.

Remaining review concerns: DLQ helper failure paths lack reliable connection cleanup; payment notification delivery is not transactional or deduplicated; DLQ replay trusts the stored payload; readiness checks database connectivity rather than complete schema compatibility; rate limiting uses per-process memory. These require resolution or explicit release acceptance with evidence, not a green-CI assumption.

Before release: deploy this exact candidate to isolated staging with valid secrets; rehearse schema upgrade and rollback on sanitized PostgreSQL data; test upload, scoped result/report access and real Stripe test-mode checkout; deliver paid, unpaid, duplicate and delayed-success events; interrupt persistence and confirm provider retry recovery; restart and reconcile payment records; verify TLS, domain callbacks and notification behavior. Record candidate SHA and sanitized provider event IDs.

Passing local tests or CI alone does not close this gate.
