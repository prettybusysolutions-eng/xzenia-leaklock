"""
domains/pretty_busy_cleaning_domain.py
Xzenia Domain Definition — Pretty Busy Cleaning

Operational intelligence for a cleaning service business:
job scheduling anomalies, client churn risk, technician capacity signals,
and billing irregularities for service delivery.

This domain demonstrates Xzenia's substrate-agnostic onboarding —
it uses ZERO revenue-recovery infrastructure yet passes the same
System 5 validator without any modifications to the substrate.
"""

from __future__ import annotations

from cognitive.domain_schema import (
    AnomalyRule,
    DomainDefinition,
    RecoveryAction,
    SignalDefinition,
)


# ── Signal definitions ────────────────────────────────────────────────────────

def _make_signals():
    return [
        SignalDefinition(
            name="job_cancellation",
            description=(
                "A scheduled cleaning job was cancelled — may indicate client churn "
                "risk or technician availability issue."
            ),
            schema={
                "job_id": "str",
                "client_id": "str",
                "technician_id": "str",
                "scheduled_at": "datetime",
                "cancelled_at": "datetime",
                "reason": "str",
            },
        ),
        SignalDefinition(
            name="job_completed",
            description="A cleaning job was completed and marked done by the technician.",
            schema={
                "job_id": "str",
                "client_id": "str",
                "technician_id": "str",
                "completed_at": "datetime",
                "duration_minutes": "int",
                "quality_rating": "float",
            },
        ),
        SignalDefinition(
            name="invoice_not_paid",
            description=(
                "A post-service invoice has not been paid within the expected window."
            ),
            schema={
                "invoice_id": "str",
                "client_id": "str",
                "amount_cents": "int",
                "due_date": "date",
                "days_overdue": "int",
            },
        ),
        SignalDefinition(
            name="technician_no_show",
            description=(
                "A technician did not arrive for a scheduled job — high churn risk event."
            ),
            schema={
                "job_id": "str",
                "technician_id": "str",
                "client_id": "str",
                "scheduled_at": "datetime",
            },
        ),
        SignalDefinition(
            name="client_complaint_filed",
            description="A client filed a formal complaint about service quality.",
            schema={
                "complaint_id": "str",
                "client_id": "str",
                "job_id": "str",
                "category": "str",
                "severity": "str",
                "filed_at": "datetime",
            },
        ),
    ]


# ── Anomaly rules ─────────────────────────────────────────────────────────────

def _cancellation_spike_check(context: dict) -> bool:
    """Return True if same-day cancellations exceed 20% of scheduled jobs."""
    scheduled = context.get("jobs_scheduled_today", 0)
    cancelled = context.get("same_day_cancellations", 0)
    if scheduled == 0:
        return False
    return (cancelled / scheduled) > 0.20


def _no_show_check(context: dict) -> bool:
    """Return True if any technician no-shows occurred in the last 24 hours."""
    return context.get("no_show_count_24h", 0) > 0


def _make_anomaly_rules():
    return [
        AnomalyRule(
            rule_id="same_day_cancellation_spike",
            description=(
                "Same-day cancellation rate exceeds 20% of scheduled jobs — "
                "indicates demand volatility or technician scheduling breakdown."
            ),
            severity="high",
            check_fn=_cancellation_spike_check,
        ),
        AnomalyRule(
            rule_id="technician_no_show",
            description=(
                "One or more technicians did not show up for a scheduled job — "
                "direct client satisfaction risk and potential churn trigger."
            ),
            severity="critical",
            check_fn=_no_show_check,
        ),
        AnomalyRule(
            rule_id="invoice_overdue_cluster",
            description=(
                "More than 3 invoices are >7 days overdue simultaneously — "
                "indicates collection process breakdown or client payment friction."
            ),
            severity="medium",
            check_fn=None,  # deferred: requires invoice aging report
        ),
        AnomalyRule(
            rule_id="quality_rating_decline",
            description=(
                "7-day rolling average quality rating dropped below 3.5/5.0 — "
                "early signal of systemic service quality degradation."
            ),
            severity="high",
            check_fn=None,  # deferred: requires rolling stats
        ),
        AnomalyRule(
            rule_id="repeat_complaint_client",
            description=(
                "Same client filed 2+ complaints within 30 days — churn imminent "
                "without proactive outreach."
            ),
            severity="medium",
            check_fn=None,  # deferred: requires complaint history query
        ),
    ]


# ── Recovery actions ──────────────────────────────────────────────────────────

def _make_recovery_actions():
    return [
        RecoveryAction(
            action_id="reassign_job_to_backup_technician",
            description=(
                "Assign a backup technician to a job that was left uncovered due to "
                "cancellation or no-show. Requires approval to avoid double-booking."
            ),
            requires_approval=True,
        ),
        RecoveryAction(
            action_id="send_client_apology_and_reschedule",
            description=(
                "Send an apology message and offer to reschedule the affected job. "
                "Requires approval before any client communication is sent."
            ),
            requires_approval=True,
        ),
        RecoveryAction(
            action_id="flag_invoice_for_collections",
            description=(
                "Mark overdue invoice as requiring collections follow-up. "
                "Internal flag only — safe to auto-execute, no external effect."
            ),
            requires_approval=False,
            execute_fn=lambda context: {
                "status": "flagged_for_collections",
                "invoice_id": context.get("invoice_id"),
            },
        ),
        RecoveryAction(
            action_id="escalate_quality_incident",
            description=(
                "Escalate a repeat-complaint or no-show event to the Coordinator "
                "for human review and decision. Always surfaces to the operator."
            ),
            requires_approval=True,
        ),
    ]


# ── Health check ──────────────────────────────────────────────────────────────

def _health_check() -> dict:
    return {
        "status": "ok",
        "message": "Pretty Busy Cleaning domain health check registered (probe runs at runtime).",
    }


# ── Domain definition ─────────────────────────────────────────────────────────

DOMAIN = DomainDefinition(
    domain_id="pretty_busy_cleaning",
    display_name="Pretty Busy Cleaning",
    version="1.0.0",
    description=(
        "Operational intelligence for a residential and commercial cleaning service. "
        "Monitors job scheduling, technician reliability, client satisfaction signals, "
        "and invoice collection health. Escalates anomalies to the Coordinator with "
        "human approval gates before any client-facing action."
    ),
    owner="Aurex / Kamm Smith",
    status="active",
    signals=_make_signals(),
    anomaly_rules=_make_anomaly_rules(),
    recovery_actions=_make_recovery_actions(),
    data_sources=[
        "scheduling_db:jobs",
        "scheduling_db:technicians",
        "invoicing_system",
        "client_crm",
        "quality_feedback_api",
    ],
    tags=["cleaning", "field-ops", "scheduling", "churn-risk", "service-quality"],
    metadata={
        "business_type": "field_services",
        "client_facing": True,
        "efe_minimizer": True,
    },
    health_check_fn=_health_check,
)
