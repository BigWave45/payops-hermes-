"""Paystack adapter contract tests using deterministic mocked API responses."""
from payops.models import Settlement, Transaction
from payops.providers import paystack as paystack_module
from payops.providers.http import ProviderError, get_json


def test_paystack_amounts_are_already_minor_units(monkeypatch):
    def fake_get_json(base_url, path, token, params):
        if path == "transaction":
            return {"status": True, "meta": {"pageCount": 1}, "data": [{
                "id": 17, "reference": "ps_ref_17", "amount": 12345,
                "currency": "NGN", "status": "success",
                "paid_at": "2026-11-05T12:00:00Z",
            }]}
        if path == "settlement":
            return {"status": True, "meta": {"pageCount": 1}, "data": [{
                "id": 9, "total_amount": 12000, "currency": "NGN",
                "status": "success", "settlement_date": "2026-11-06",
            }]}
        raise AssertionError(path)

    monkeypatch.setattr(paystack_module, "get_json", fake_get_json)
    adapter = paystack_module.Paystack("test-key")
    transactions = adapter.transactions("2026-11-01", "2026-11-06", 3)
    settlements = adapter.settlements("2026-11-01", "2026-11-06", 3)
    assert transactions == [
        Transaction("paystack", "17", "ps_ref_17", 12345, "NGN", "success", "2026-11-05T12:00:00Z")
    ]
    assert settlements == [
        Settlement("paystack", "9", "NGN", 12000, "success", "2026-11-06")
    ]


def test_legacy_flutterwave_v3_host_is_not_allowed_by_static_key_client():
    try:
        get_json("https://api.flutterwave.com", "v3/transactions", "legacy-key")
    except ProviderError as exc:
        assert "not permitted" in str(exc)
    else:
        raise AssertionError("legacy Flutterwave v3 host must not be allowed")
