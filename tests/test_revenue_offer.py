import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OFFER = ROOT / "docs" / "index.html"
SAMPLE = ROOT / "docs" / "sample-audit.html"
AGENT_OFFER = ROOT / "docs" / "agent-offer.json"
AGENT_FIT_SCHEMA = ROOT / "docs" / "schemas" / "agent-fit-request.schema.json"
AGENT_AUTH_SCHEMA = ROOT / "docs" / "schemas" / "agent-purchase-authorization.schema.json"
AGENT_RECEIPT_SCHEMA = ROOT / "docs" / "schemas" / "agent-receipt.schema.json"
LLMS = ROOT / "docs" / "llms.txt"
INTAKE = ROOT / ".github" / "ISSUE_TEMPLATE" / "revenue-leak-audit.yml"


def test_offer_has_price_truth_boundary_and_stable_intake():
    content = OFFER.read_text(encoding="utf-8")
    assert "$199" in content
    assert "does not promise" in content
    assert "prettybusysolutions@gmail.com" in content
    assert "revenue-leak-audit.yml" in content
    assert "https://buy.stripe.com/7sYbJ0dgk3RVesg88u0kE0j" in content
    assert "Fit confirmed? Pay $199 securely" in content
    assert "client_reference_id=" in content
    assert "source=" in content
    assert "sample-audit.html" in content
    assert "agent-offer.json" in content
    assert "trycloudflare.com" not in content


def test_sample_audit_is_clearly_synthetic_and_preserves_truth_boundaries():
    content = SAMPLE.read_text(encoding="utf-8")
    assert "Synthetic example only" in content
    assert "Nothing on this page represents a real customer" in content
    assert "$0" in content
    assert "Verified recoverable revenue claimed" in content
    assert "does not prove they are collectible" in content
    assert "does not promise recovery" in content
    assert "prettybusysolutions@gmail.com" in content


def test_public_intake_rejects_sensitive_data():
    content = INTAKE.read_text(encoding="utf-8")
    assert "Do not include billing exports" in content
    assert "I have not included sensitive billing or customer data" in content
    assert "does not guarantee recovered revenue" in content


def test_agent_offer_is_machine_readable_and_requires_human_authorization():
    offer = json.loads(AGENT_OFFER.read_text(encoding="utf-8"))
    assert offer["offer_id"] == "xzenia.revenue-leak-evidence-audit.usd-199.v1"
    assert offer["price"] == {
        "amount": 199,
        "currency": "USD",
        "type": "one_time",
        "price_version": "2026-06-11",
    }
    assert offer["purchase"]["automatic_charge_allowed"] is False
    assert "fit_confirmed_by_provider" in offer["purchase"]["required_before_payment"]
    assert offer["handoff"]["private_handoff_required"] is True
    assert offer["security"]["x402_payment_enabled"] is False
    assert "trycloudflare.com" not in json.dumps(offer)


def test_agent_schemas_lock_price_authorization_and_receipt_states():
    fit = json.loads(AGENT_FIT_SCHEMA.read_text(encoding="utf-8"))
    authorization = json.loads(AGENT_AUTH_SCHEMA.read_text(encoding="utf-8"))
    receipt = json.loads(AGENT_RECEIPT_SCHEMA.read_text(encoding="utf-8"))
    assert "operator_authorized" in fit["required"]
    assert authorization["properties"]["operator_approved"]["const"] is True
    assert authorization["properties"]["amount"]["const"] == 199
    assert authorization["properties"]["currency"]["const"] == "USD"
    assert "pending_private_handoff" in receipt["properties"]["fulfillment_status"]["enum"]
    assert "delivered" in receipt["properties"]["fulfillment_status"]["enum"]


def test_llms_discovery_preserves_payment_and_data_boundaries():
    content = LLMS.read_text(encoding="utf-8")
    assert "agent-offer.json" in content
    assert "199 USD" in content
    assert "Obtain operator authorization before purchase" in content
    assert "Do not transmit billing exports or customer data publicly" in content
