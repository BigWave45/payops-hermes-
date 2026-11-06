"""Provider adapter contract tests using deterministic mocked API responses."""
from payops.models import Settlement, Transaction
from payops.providers import flutterwave as flutterwave_module
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


def test_flutterwave_v3_secret_key_transactions_and_settlements(monkeypatch):
    api_calls = []

    def fake_get(base_url, path, token, params):
        api_calls.append((base_url, path, token, dict(params)))
        if path == "v3/transactions":
            status = params["status"]
            page = params["page"]
            total_pages = 2 if status == "successful" else 1
            return {
                "status": "success",
                "meta": {"page_info": {"total_pages": total_pages, "current_page": page}},
                "data": [{
                    "id": 100 + page,
                    "tx_ref": f"fw_{status}_{page}",
                    "charged_amount": "123.45" if page == 1 else "1.00",
                    "currency": "NGN",
                    "status": status,
                    "created_at": "2026-11-05T12:00:00Z",
                }],
            }
        if path == "v3/settlements":
            return {
                "status": "success",
                "meta": {"page_info": {"total_pages": 1, "current_page": 1}},
                "data": [{
                    "id": 9, "net_amount": "120.00",
                    "gross_amount": "125.00", "currency": "NGN",
                    "status": "completed", "processed_date": "2026-11-06",
                }],
            }
        raise AssertionError(path)

    monkeypatch.setattr(flutterwave_module, "get_json", fake_get)
    adapter = flutterwave_module.Flutterwave("test-secret-key")
    transactions = adapter.transactions("2026-11-01", "2026-11-06", 3)
    settlements = adapter.settlements("2026-11-01", "2026-11-06", 3)

    assert [item.amount_minor for item in transactions] == [12345, 100, 12345]
    assert [item.status for item in transactions] == ["successful", "successful", "failed"]
    assert [item.reference for item in transactions] == [
        "fw_successful_1", "fw_successful_2", "fw_failed_1"
    ]
    assert [item.amount_minor for item in settlements] == [12000]
    assert [item.settlement_id for item in settlements] == ["9"]
    assert all(call[0] == "https://api.flutterwave.com" for call in api_calls)
    assert all(call[2] == "test-secret-key" for call in api_calls)
    assert [call[3]["status"] for call in api_calls if call[1] == "v3/transactions"] == [
        "successful", "successful", "failed"
    ]
    assert any("pending transactions are not included" in warning for warning in adapter.warnings)


def test_flutterwave_v3_discloses_page_cap(monkeypatch):
    def fake_get(base_url, path, token, params):
        if path == "v3/transactions":
            return {
                "status": "success",
                "meta": {"page_info": {"total_pages": 3}},
                "data": [{
                    "id": params["page"], "tx_ref": f"ref_{params['status']}_{params['page']}",
                    "amount": "1.00", "currency": "NGN", "status": params["status"],
                }],
            }
        raise AssertionError(path)

    monkeypatch.setattr(flutterwave_module, "get_json", fake_get)
    adapter = flutterwave_module.Flutterwave("test-secret-key")
    records = adapter.transactions("2026-11-01", "2026-11-06", 1)
    assert len(records) == 2
    assert len([warning for warning in adapter.warnings if "fetched 1 of 3 pages" in warning]) == 2


def test_flutterwave_requires_secret_key():
    try:
        flutterwave_module.Flutterwave("")
    except ProviderError as exc:
        assert "secret key is not configured" in str(exc)
    else:
        raise AssertionError("missing secret key should be rejected")


def test_http_client_rejects_unapproved_hosts():
    try:
        get_json("https://example.com", "/anything", "secret")
    except ProviderError as exc:
        assert "not permitted" in str(exc)
    else:
        raise AssertionError("unapproved host should be rejected")
