from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OFFER = ROOT / "docs" / "index.html"
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
    assert "trycloudflare.com" not in content


def test_public_intake_rejects_sensitive_data():
    content = INTAKE.read_text(encoding="utf-8")
    assert "Do not include billing exports" in content
    assert "I have not included sensitive billing or customer data" in content
    assert "does not guarantee recovered revenue" in content
