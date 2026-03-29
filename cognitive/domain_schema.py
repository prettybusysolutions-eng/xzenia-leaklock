"""
cognitive/domain_schema.py
Xzenia System 5 — DomainDefinition dataclass

Every domain onboarded into Xzenia must declare itself via this contract.
The schema is intentionally substrate-agnostic: it describes WHAT a domain
does, not HOW its infrastructure works.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class SignalDefinition:
    """Describes a single signal (data point) the domain can emit or consume."""
    name: str                         # machine-friendly slug, e.g. "stripe_charge_failed"
    description: str                  # human-readable intent
    schema: Dict[str, str]            # field_name -> type hint (str representation)
    required: bool = True             # whether this signal is mandatory for domain health


@dataclass
class AnomalyRule:
    """Describes a heuristic or causal rule for detecting domain anomalies."""
    rule_id: str                      # unique slug
    description: str
    severity: str                     # "critical" | "high" | "medium" | "low"
    check_fn: Optional[Callable]      # callable(context: dict) -> bool — None = deferred


@dataclass
class RecoveryAction:
    """Describes an action the domain can take to recover from an anomaly."""
    action_id: str
    description: str
    requires_approval: bool = True    # always True unless explicitly safe to auto-execute
    execute_fn: Optional[Callable] = None


@dataclass
class DomainDefinition:
    """
    The universal onboarding contract for any Xzenia domain.

    A domain is a coherent business area (e.g. revenue-recovery, cleaning-ops)
    that contributes signals, anomaly rules, and recovery actions to the
    Xzenia cognitive loop. It must declare all of these upfront so the
    System 5 validator can confirm completeness before activation.
    """

    # ── Identity ─────────────────────────────────────────────────────────────
    domain_id: str                    # machine slug, e.g. "revenue_recovery"
    display_name: str                 # human label, e.g. "Revenue Recovery"
    version: str                      # semver string, e.g. "1.0.0"
    description: str                  # what this domain does, one paragraph max

    # ── Owner & lifecycle ────────────────────────────────────────────────────
    owner: str                        # team or person responsible
    status: str = "active"            # "active" | "inactive" | "experimental"

    # ── Signals ──────────────────────────────────────────────────────────────
    signals: List[SignalDefinition] = field(default_factory=list)

    # ── Anomaly detection ────────────────────────────────────────────────────
    anomaly_rules: List[AnomalyRule] = field(default_factory=list)

    # ── Recovery ─────────────────────────────────────────────────────────────
    recovery_actions: List[RecoveryAction] = field(default_factory=list)

    # ── Data sources ─────────────────────────────────────────────────────────
    data_sources: List[str] = field(default_factory=list)
    # e.g. ["stripe", "postgres:saas_detected_leaks", "csv_export"]

    # ── Metadata (free-form) ─────────────────────────────────────────────────
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    # ── Health probe ─────────────────────────────────────────────────────────
    health_check_fn: Optional[Callable] = None
    # callable() -> dict with keys: {"status": "ok"|"degraded"|"down", "message": str}
