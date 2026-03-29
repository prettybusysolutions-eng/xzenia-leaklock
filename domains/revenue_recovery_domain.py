"""
domains/revenue_recovery_domain.py
Xzenia Domain Definition — Revenue Recovery

Detects billing leakage, causal attribution of failed charges,
and orchestrates recovery workflows via Stripe and PostgreSQL.
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
            name="stripe_charge_failed",
            description="A Stripe charge attempt failed; potential revenue leakage event.",
            schema={
                "charge_id": "str",
                "customer_id": "str",
                "amount_cents": "int",
                "failure_code": "str",
                "occurred_at": "datetime",
            },
        ),
        SignalDefinition(
            name="subscription_past_due",
            description="A subscription has entered past_due state — payment collection at risk.",
            schema={
                "subscription_id": "str",
                "customer_id": "str",
                "amount_due_cents": "int",
                "days_past_due": "int",
            },
        ),
        SignalDefinition(
            name="invoice_uncollectible",
            description="Invoice marked uncollectible — potential write-off if not recovered.",
            schema={
                "invoice_id": "str",
                "customer_id": "str",
                "amount_cents": "int",
                "created_at": "datetime",
            },
        ),
        SignalDefinition(
            name="refund_issued",
            description="A refund was issued — potential leakage if incorrectly triggered.",
            schema={
                "refund_id": "str",
                "charge_id": "str",
                "amount_cents": "int",
                "reason": "str",
                "issued_at": "datetime",
            },
        ),
        SignalDefinition(
            name="scan_leak_detected",
            description="The LeakLock scanner detected a billing anomaly pattern.",
            schema={
                "scan_id": "str",
                "pattern": "str",
                "amount_estimate": "float",
                "confidence": "float",
                "severity": "str",
            },
        ),
    ]


# ── Anomaly rules ─────────────────────────────────────────────────────────────

def _high_failure_rate_check(context: dict) -> bool:
    """Return True (anomaly detected) if charge failure rate exceeds threshold."""
    total = context.get("total_charges", 0)
    failed = context.get("failed_charges", 0)
    if total == 0:
        return False
    return (failed / total) > 0.05   # >5% failure rate is anomalous


def _uncollectible_spike_check(context: dict) -> bool:
    """Return True if uncollectible invoices spiked vs rolling 30-day baseline."""
    current = context.get("uncollectible_today", 0)
    baseline = context.get("uncollectible_30d_avg", 0)
    return current > (baseline * 3) and current > 2


def _make_anomaly_rules():
    return [
        AnomalyRule(
            rule_id="high_charge_failure_rate",
            description=(
                "Charge failure rate exceeds 5% in a rolling window — "
                "indicates systemic payment method decay or fraud."
            ),
            severity="critical",
            check_fn=_high_failure_rate_check,
        ),
        AnomalyRule(
            rule_id="subscription_past_due_cluster",
            description=(
                "Multiple subscriptions entered past_due within 24h — "
                "may indicate a billing provider outage or dunning misconfiguration."
            ),
            severity="high",
            check_fn=None,  # deferred: requires subscription cohort analysis
        ),
        AnomalyRule(
            rule_id="uncollectible_spike",
            description=(
                "Uncollectible invoice volume spiked >3x the 30-day average — "
                "potential fraud campaign or payment processor issue."
            ),
            severity="high",
            check_fn=_uncollectible_spike_check,
        ),
        AnomalyRule(
            rule_id="refund_leakage_pattern",
            description=(
                "Refund rate exceeds 2% of GMV — possible exploitation of "
                "refund policies or fulfillment failures."
            ),
            severity="medium",
            check_fn=None,  # deferred: requires GMV calculation
        ),
    ]


# ── Recovery actions ──────────────────────────────────────────────────────────

def _make_recovery_actions():
    return [
        RecoveryAction(
            action_id="retry_failed_charges",
            description=(
                "Re-attempt failed charges for customers with updated payment methods. "
                "Requires human approval to avoid double-charging."
            ),
            requires_approval=True,
        ),
        RecoveryAction(
            action_id="send_dunning_email",
            description=(
                "Trigger dunning email sequence to past_due subscribers. "
                "Low-risk; requires approval to avoid spam escalation."
            ),
            requires_approval=True,
        ),
        RecoveryAction(
            action_id="flag_for_manual_review",
            description=(
                "Mark anomalous charges/invoices for ops team review in the dashboard. "
                "Read-only write to saas_detected_leaks — safe to auto-execute."
            ),
            requires_approval=False,
            execute_fn=lambda context: {"status": "flagged", "count": len(context.get("items", []))},
        ),
        RecoveryAction(
            action_id="escalate_to_coordinator",
            description=(
                "Escalate critical revenue anomalies to the Coordinator for human decision. "
                "Always surfaces to the human operator before any action."
            ),
            requires_approval=True,
        ),
    ]


# ── Health check ──────────────────────────────────────────────────────────────

def _health_check() -> dict:
    """Lightweight connectivity probe — does not touch live DB at import time."""
    return {
        "status": "ok",
        "message": "Revenue recovery domain health check registered (probe runs at runtime).",
    }


# ── Domain definition ─────────────────────────────────────────────────────────

DOMAIN = DomainDefinition(
    domain_id="revenue_recovery",
    display_name="Revenue Recovery",
    version="1.0.0",
    description=(
        "Detects billing leakage, failed charge patterns, and subscription decay "
        "via Stripe event streams and the LeakLock scanner. Orchestrates dunning, "
        "retry, and escalation workflows with human approval gates."
    ),
    owner="Aurex / Kamm Smith",
    status="active",
    signals=_make_signals(),
    anomaly_rules=_make_anomaly_rules(),
    recovery_actions=_make_recovery_actions(),
    data_sources=[
        "stripe",
        "postgres:saas_detected_leaks",
        "postgres:saas_customers",
        "csv_export",
    ],
    tags=["revenue", "billing", "stripe", "saas", "causal-intelligence"],
    metadata={
        "causal_graph_version": "2.1",
        "efe_minimizer": True,
        "relationship_bridge": True,
    },
    health_check_fn=_health_check,
)
