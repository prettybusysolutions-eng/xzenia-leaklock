-- System 6 — Layer 4 lifecycle hardening
-- Approval -> execution -> measured outcome loop with open-action dedupe.

ALTER TABLE saas_consequence_actions
    ADD COLUMN IF NOT EXISTS decision_actor TEXT,
    ADD COLUMN IF NOT EXISTS decided_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS execution_actor TEXT,
    ADD COLUMN IF NOT EXISTS execution_updated_at TIMESTAMPTZ;

CREATE UNIQUE INDEX IF NOT EXISTS idx_consequence_actions_case_active
    ON saas_consequence_actions(case_id)
    WHERE approval_status IN ('pending', 'approved');
