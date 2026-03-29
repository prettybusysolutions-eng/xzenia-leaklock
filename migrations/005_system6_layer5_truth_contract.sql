-- System 6 Layer 5: identity binding, evidence requirement, verification scaffold

ALTER TABLE saas_consequence_actions
    ADD COLUMN IF NOT EXISTS decision_actor_id TEXT,
    ADD COLUMN IF NOT EXISTS decision_actor_type TEXT,
    ADD COLUMN IF NOT EXISTS decision_actor_payload JSONB,
    ADD COLUMN IF NOT EXISTS decision_actor_is_legacy BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS execution_actor_id TEXT,
    ADD COLUMN IF NOT EXISTS execution_actor_type TEXT,
    ADD COLUMN IF NOT EXISTS execution_actor_payload JSONB,
    ADD COLUMN IF NOT EXISTS execution_actor_is_legacy BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS execution_verification_status TEXT NOT NULL DEFAULT 'unverified',
    ADD COLUMN IF NOT EXISTS execution_verification_path TEXT,
    ADD COLUMN IF NOT EXISTS execution_verification_notes TEXT,
    ADD COLUMN IF NOT EXISTS execution_verified_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS outcome_actor_id TEXT,
    ADD COLUMN IF NOT EXISTS outcome_actor_type TEXT,
    ADD COLUMN IF NOT EXISTS outcome_actor_payload JSONB,
    ADD COLUMN IF NOT EXISTS outcome_actor_is_legacy BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS outcome_evidence JSONB NOT NULL DEFAULT '[]'::jsonb,
    ADD COLUMN IF NOT EXISTS outcome_evidence_count INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS outcome_verification_status TEXT NOT NULL DEFAULT 'unverified',
    ADD COLUMN IF NOT EXISTS outcome_verification_path TEXT,
    ADD COLUMN IF NOT EXISTS outcome_verification_notes TEXT,
    ADD COLUMN IF NOT EXISTS outcome_verified_at TIMESTAMPTZ;

UPDATE saas_consequence_actions
SET decision_actor_id = COALESCE(decision_actor_id, decision_actor),
    decision_actor_type = COALESCE(decision_actor_type, CASE WHEN decision_actor IS NOT NULL THEN 'legacy_string_actor' ELSE NULL END),
    decision_actor_payload = COALESCE(
        decision_actor_payload,
        CASE
            WHEN decision_actor IS NOT NULL THEN jsonb_build_object(
                'actor_id', decision_actor,
                'actor_type', 'legacy_string_actor',
                'display_name', decision_actor,
                'legacy', TRUE,
                'raw_actor', decision_actor
            )
            ELSE NULL
        END
    ),
    decision_actor_is_legacy = CASE
        WHEN decision_actor IS NOT NULL AND decision_actor_payload IS NULL THEN TRUE
        ELSE decision_actor_is_legacy
    END,
    execution_actor_id = COALESCE(execution_actor_id, execution_actor),
    execution_actor_type = COALESCE(execution_actor_type, CASE WHEN execution_actor IS NOT NULL THEN 'legacy_string_actor' ELSE NULL END),
    execution_actor_payload = COALESCE(
        execution_actor_payload,
        CASE
            WHEN execution_actor IS NOT NULL THEN jsonb_build_object(
                'actor_id', execution_actor,
                'actor_type', 'legacy_string_actor',
                'display_name', execution_actor,
                'legacy', TRUE,
                'raw_actor', execution_actor
            )
            ELSE NULL
        END
    ),
    execution_actor_is_legacy = CASE
        WHEN execution_actor IS NOT NULL AND execution_actor_payload IS NULL THEN TRUE
        ELSE execution_actor_is_legacy
    END;

ALTER TABLE saas_consequence_actions
    ADD CONSTRAINT chk_system6_execution_verification_status
        CHECK (execution_verification_status IN ('unverified', 'pending', 'verified', 'disputed')),
    ADD CONSTRAINT chk_system6_outcome_verification_status
        CHECK (outcome_verification_status IN ('unverified', 'pending', 'verified', 'disputed')),
    ADD CONSTRAINT chk_system6_outcome_evidence_count_nonnegative
        CHECK (outcome_evidence_count >= 0),
    ADD CONSTRAINT chk_system6_outcome_evidence_shape
        CHECK (jsonb_typeof(outcome_evidence) = 'array');
