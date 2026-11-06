"""Provider adapter contract tests using deterministic mocked API responses."""
from payops.models import Settlement, Transaction
from payops.providers import flutterwave as flutterwave_module
from payops.providers import paystack as paystack_module
from payops.providers.http import ProviderError, get_json


def _patch_hermes_request(monkeypatch, handler):
    import sys
    import types

    package = types.ModuleType("hermes_cli")
    package.__path__ = []
    module = types.ModuleType("hermes_cli.plugin_provider_requests")
    module.credentialed_provider_request = handler
    monkeypatch.setitem(sys.modules, "hermes_cli", package)
    monkeypatch.setitem(sys.modules, "hermes_cli.plugin_provider_requests", module)


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


def test_flutterwave_v4_oauth_transactions_and_settlements(monkeypatch):
    api_calls = []

    class Response:
        status = 200

        def __init__(self, payload):
            self.payload = payload

        def json(self):
            return self.payload

    def fake_request(provider, method, url, *, headers, timeout):
        from urllib.parse import urlsplit, parse_qs
        parsed = urlsplit(url)
        params = parse_qs(parsed.query)
        api_calls.append((provider, method, parsed.netloc, parsed.path, params, headers, timeout))
        page = int(params.get("page", ["1"])[0])
        if parsed.path == "/charges":
            status = params["status"][0]
            return Response({
                "status": "success",
                "meta": {"page_info": {"total_pages": 2 if status == "succeeded" else 1}},
                "data": [{
                    "id": f"chg_{status}_{page}",
                    "reference": f"fw_{status}_{page}",
                    "amount": "123.45" if page == 1 else "1.00",
                    "currency": "NGN",
                    "status": status,
                    "created_datetime": "2026-11-05T12:00:00Z",
                }],
            })
        if parsed.path == "/settlements":
            return Response({
                "status": "success",
                "meta": {"page_info": {"total_pages": 1}},
                "data": [{
                    "id": "stm_9", "net_amount": "120.00",
                    "gross_amount": "125.00", "currency": "NGN",
                    "status": "completed", "due_datetime": "2026-11-06T00:00:00Z",
                    "created_datetime": "2026-11-05T00:00:00Z",
                }],
            })
        raise AssertionError(parsed.path)

    _patch_hermes_request(monkeypatch, fake_request)
    adapter = flutterwave_module.Flutterwave()
    transactions = adapter.transactions("2026-11-01", "2026-11-06", 3)
    settlements = adapter.settlements("2026-11-01", "2026-11-06", 3)

    assert [item.amount_minor for item in transactions] == [12345, 100, 12345, 12345, 12345]
    assert [item.status for item in transactions] == [
        "succeeded", "succeeded", "pending", "failed", "voided"
    ]
    assert [item.reference for item in transactions] == [
        "fw_succeeded_1", "fw_succeeded_2", "fw_pending_1", "fw_failed_1", "fw_voided_1"
    ]
    assert [item.amount_minor for item in settlements] == [12000]
    assert [item.settlement_id for item in settlements] == ["stm_9"]
    assert all(call[0] == "flutterwave" and call[1] == "GET" for call in api_calls)
    assert all(call[2] == "developersandbox-api.flutterwave.com" for call in api_calls)
    assert all(call[5]["Accept"] == "application/json" for call in api_calls)
    assert [call[4]["status"][0] for call in api_calls if call[3] == "/charges"] == [
        "succeeded", "succeeded", "pending", "failed", "voided"
    ]
    assert all("from" in call[4] and "to" in call[4] for call in api_calls)


def test_flutterwave_v4_discloses_page_cap(monkeypatch):
    class Response:
        status = 200

        @staticmethod
        def json():
            return {
                "status": "success",
                "meta": {"page_info": {"total_pages": 3}},
                "data": [{
                    "id": "chg_1", "reference": "ref_1", "amount": "1.00",
                    "currency": "NGN", "status": "succeeded",
                }],
            }

    calls = []
    def fake_request(provider, method, url, **kwargs):
        calls.append(url)
        return Response()

    _patch_hermes_request(monkeypatch, fake_request)
    adapter = flutterwave_module.Flutterwave()
    records = adapter.transactions("2026-11-01", "2026-11-06", 1)
    assert len(records) == 4
    assert len([warning for warning in adapter.warnings if "fetched 1 of 3 pages" in warning]) == 4


def test_flutterwave_rejects_invalid_environment():
    try:
        flutterwave_module.Flutterwave("live")
    except ProviderError as exc:
        assert "environment" in str(exc)
    else:
        raise AssertionError("invalid environment should be rejected")


def test_flutterwave_rejects_non_success_and_bad_response(monkeypatch):
    class Response:
        status = 200

        @staticmethod
        def json():
            return {"status": "failed", "data": []}

    _patch_hermes_request(monkeypatch, lambda *args, **kwargs: Response())
    adapter = flutterwave_module.Flutterwave()
    try:
        adapter.transactions("2026-11-01", "2026-11-06", 1)
    except ProviderError as exc:
        assert "unsuccessful" in str(exc)
    else:
        raise AssertionError("failed API status should be rejected")


def test_legacy_flutterwave_v3_host_is_not_allowed_by_static_key_client():
    try:
        get_json("https://api.flutterwave.com", "v3/transactions", "legacy-key")
    except ProviderError as exc:
        assert "not permitted" in str(exc)
    else:
        raise AssertionError("legacy Flutterwave v3 host must not be allowed")
