-- System 6 — Consequence Engine scaffold
-- Build from truth, not performance.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS saas_consequence_cases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain TEXT NOT NULL,
    source_system TEXT NOT NULL,
    source_event_id TEXT NOT NULL,
    scan_id TEXT,
    customer_ref TEXT,
    anomaly_type TEXT NOT NULL,
    evidence JSONB NOT NULL DEFAULT '{}'::jsonb,
    is_synthetic BOOLEAN NOT NULL DEFAULT FALSE,
    status TEXT NOT NULL DEFAULT 'detected',
    detected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(domain, source_system, source_event_id)
);

CREATE TABLE IF NOT EXISTS saas_consequence_actions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id UUID NOT NULL REFERENCES saas_consequence_cases(id) ON DELETE CASCADE,
    recommendation TEXT NOT NULL,
    causal_hypothesis TEXT,
    requires_approval BOOLEAN NOT NULL DEFAULT TRUE,
    approval_status TEXT NOT NULL DEFAULT 'pending',
    approved_by TEXT,
    decision_notes TEXT,
    executed_at TIMESTAMPTZ,
    execution_status TEXT NOT NULL DEFAULT 'pending',
    execution_notes TEXT,
    outcome_type TEXT,
    outcome_value NUMERIC(12, 2),
    outcome_currency TEXT DEFAULT 'USD',
    outcome_notes TEXT,
    measured_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_consequence_cases_domain_detected
    ON saas_consequence_cases(domain, detected_at DESC);
CREATE INDEX IF NOT EXISTS idx_consequence_cases_synthetic
    ON saas_consequence_cases(is_synthetic);
CREATE INDEX IF NOT EXISTS idx_consequence_actions_case
    ON saas_consequence_actions(case_id);
