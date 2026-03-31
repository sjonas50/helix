"""Tests for PII detection and stripping."""

from helix.memory.pii import detect_pii, has_pii, strip_pii


class TestDetectPII:
    def test_detect_email(self) -> None:
        found = detect_pii("Contact john@example.com for details")
        assert "email" in found
        assert "john@example.com" in found["email"]

    def test_detect_phone(self) -> None:
        found = detect_pii("Call us at 555-123-4567")
        assert "phone" in found

    def test_detect_ssn(self) -> None:
        found = detect_pii("SSN: 123-45-6789")
        assert "ssn" in found

    def test_detect_credit_card(self) -> None:
        found = detect_pii("Card: 4111-1111-1111-1111")
        assert "credit_card" in found

    def test_detect_ip(self) -> None:
        found = detect_pii("Server at 192.168.1.100")
        assert "ip_address" in found

    def test_no_pii(self) -> None:
        found = detect_pii("This is a normal business document about Q1 revenue")
        assert not found


class TestStripPII:
    def test_strip_email(self) -> None:
        cleaned, counts = strip_pii("Email john@example.com now")
        assert "[EMAIL_REDACTED]" in cleaned
        assert "john@example.com" not in cleaned
        assert counts["email"] == 1

    def test_strip_multiple_types(self) -> None:
        text = "Contact john@example.com at 555-123-4567"
        cleaned, counts = strip_pii(text)
        assert "john@example.com" not in cleaned
        assert "555-123-4567" not in cleaned
        assert counts["email"] == 1
        assert counts["phone"] == 1

    def test_strip_disabled(self) -> None:
        text = "Email john@example.com"
        cleaned, counts = strip_pii(text, enabled=False)
        assert cleaned == text
        assert counts == {}

    def test_strip_preserves_non_pii(self) -> None:
        text = "Revenue was $10M in Q1 2026"
        cleaned, counts = strip_pii(text)
        assert cleaned == text
        assert counts == {}


class TestHasPII:
    def test_has_pii_true(self) -> None:
        assert has_pii("john@example.com")

    def test_has_pii_false(self) -> None:
        assert not has_pii("Regular business text")
