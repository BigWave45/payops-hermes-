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


def test_flutterwave_v4_oauth_charges_and_settlements(monkeypatch):
    token_calls = []
    api_calls = []

    def fake_post(url, fields):
        token_calls.append((url, dict(fields)))
        return {"access_token": "temporary-token", "expires_in": 600}

    def fake_get(base_url, path, token, params, headers=None):
        api_calls.append((base_url, path, token, dict(params), dict(headers or {})))
        if path == "charges":
            status = params["status"]
            page = params["page"]
            total_pages = 2 if status == "succeeded" else 1
            return {
                "status": "success",
                "meta": {"page_info": {"total_pages": total_pages, "current_page": page}},
                "data": [{
                    "id": f"chg_{status}_{page}",
                    "reference": f"fw_{status}_{page}",
                    "amount": "123.45" if page == 1 else "1.00",
                    "currency": "NGN",
                    "status": status,
                    "created_datetime": "2026-11-05T12:00:00Z",
                }],
            }
        if path == "settlements":
            return {
                "status": "success",
                "meta": {"page_info": {"total_pages": 1, "current_page": 1}},
                "data": [{
                    "id": "stm_4", "net_amount": "120.00",
                    "gross_amount": "125.00", "currency": "NGN",
                    "status": "completed", "created_datetime": "2026-11-06T00:00:00Z",
                }],
            }
        raise AssertionError(path)

    monkeypatch.setattr(flutterwave_module, "post_form_json", fake_post)
    monkeypatch.setattr(flutterwave_module, "get_json", fake_get)
    adapter = flutterwave_module.Flutterwave("client-id", "client-secret")
    transactions = adapter.transactions("2026-11-01", "2026-11-06", 3)
    settlements = adapter.settlements("2026-11-01", "2026-11-06", 3)

    assert token_calls == [(
        flutterwave_module.TOKEN_URL,
        {"client_id": "client-id", "client_secret": "client-secret", "grant_type": "client_credentials"},
    )]
    assert [item.amount_minor for item in transactions] == [12345, 100, 12345, 100, 12345]
    assert [item.status for item in transactions] == [
        "succeeded", "succeeded", "pending", "failed", "voided"
    ]
    assert [item.reference for item in transactions] == [
        "fw_succeeded_1", "fw_succeeded_2", "fw_pending_1",
        "fw_failed_1", "fw_voided_1",
    ]
    assert [item.amount_minor for item in settlements] == [12000]
    assert [item.settlement_id for item in settlements] == ["stm_4"]
    charge_calls = [call for call in api_calls if call[1] == "charges"]
    assert [call[3]["status"] for call in charge_calls] == [
        "succeeded", "succeeded", "pending", "failed", "voided"
    ]
    assert all(call[2] == "temporary-token" for call in api_calls)
    assert all(call[4].get("X-Trace-Id") for call in api_calls)


def test_flutterwave_discloses_page_cap(monkeypatch):
    def fake_post(url, fields):
        return {"access_token": "temporary-token"}

    def fake_get(base_url, path, token, params, headers=None):
        if path == "charges":
            return {
                "status": "success",
                "meta": {"page_info": {"total_pages": 3}},
                "data": [{
                    "id": f"chg_{params['status']}_{params['page']}",
                    "reference": f"ref_{params['status']}_{params['page']}",
                    "amount": "1.00", "currency": "NGN",
                    "status": params["status"],
                }],
            }
        raise AssertionError(path)

    monkeypatch.setattr(flutterwave_module, "post_form_json", fake_post)
    monkeypatch.setattr(flutterwave_module, "get_json", fake_get)
    adapter = flutterwave_module.Flutterwave("client-id", "client-secret")
    records = adapter.transactions("2026-11-01", "2026-11-06", 1)
    assert len(records) == 4
    assert len(adapter.warnings) == 4
    assert all("fetched 1 of 3 pages" in warning for warning in adapter.warnings)


def test_flutterwave_requires_oauth_credentials():
    try:
        flutterwave_module.Flutterwave("", "")
    except ProviderError as exc:
        assert "credentials are not configured" in str(exc)
    else:
        raise AssertionError("missing OAuth credentials should be rejected")


def test_http_client_rejects_unapproved_hosts():
    try:
        get_json("https://example.com", "/anything", "secret")
    except ProviderError as exc:
        assert "not permitted" in str(exc)
    else:
        raise AssertionError("unapproved host should be rejected")
