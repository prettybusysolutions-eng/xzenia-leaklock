from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OFFER = ROOT / "docs" / "index.html"
SAMPLE = ROOT / "docs" / "sample-audit.html"
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
