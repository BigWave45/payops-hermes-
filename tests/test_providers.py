"""Provider adapter contract tests using deterministic mocked API responses."""
from payops.models import Settlement, Transaction
from payops.providers import flutterwave as flutterwave_module
from payops.providers import paystack as paystack_module
from payops.providers.http import ProviderError, get_json


def test_paystack_amounts_are_already_minor_units(monkeypatch):
    def fake_get_json(base_url, path, token, params):
        if path == "transaction":
            return {"status": True, "data": [{
                "id": 17,
                "reference": "ps_ref_17",
                "amount": 12345,
                "currency": "NGN",
                "status": "success",
                "paid_at": "2026-11-05T12:00:00Z",
            }]}
        if path == "settlement":
            return {"status": True, "data": [{
                "id": 9,
                "total_amount": 12000,
                "currency": "NGN",
                "status": "success",
                "settlement_date": "2026-11-06",
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


def test_flutterwave_major_units_convert_to_minor_units(monkeypatch):
    calls = []

    def fake_get_json(base_url, path, token, params):
        calls.append((path, dict(params)))
        if path == "transactions":
            return {"status": "success", "data": [{
                "id": 23,
                "tx_ref": "fw_ref_23",
                "amount": "123.45",
                "currency": "NGN",
                "status": params["status"],
                "created_at": "2026-11-05T12:00:00Z",
            }]}
        if path == "settlements":
            return {"status": "success", "data": [{
                "id": "settlement-4",
                "amount": "120.00",
                "currency": "NGN",
                "status": "completed",
                "created_at": "2026-11-06T00:00:00Z",
            }]}
        raise AssertionError(path)

    monkeypatch.setattr(flutterwave_module, "get_json", fake_get_json)
    adapter = flutterwave_module.Flutterwave("test-key")

    transactions = adapter.transactions("2026-11-01", "2026-11-06", 2)
    settlements = adapter.settlements("2026-11-01", "2026-11-06", 2)

    assert [item.amount_minor for item in transactions] == [12345, 12345]
    assert [item.status for item in transactions] == ["successful", "failed"]
    assert [item.amount_minor for item in settlements] == [12000]
    assert [item.provider for item in settlements] == ["flutterwave"]
    assert [params["status"] for path, params in calls if path == "transactions"] == [
        "successful", "failed"
    ]


def test_http_client_rejects_unapproved_hosts():
    try:
        get_json("https://example.com", "/anything", "secret")
    except ProviderError as exc:
        assert "not permitted" in str(exc)
    else:
        raise AssertionError("unapproved host should be rejected")
