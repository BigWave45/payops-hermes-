"""Read-only Flutterwave v4 adapter using Hermes-managed OAuth credentials."""
from datetime import datetime, timezone
from urllib.parse import urlencode
from uuid import uuid4

from ..models import Transaction, Settlement
from ..money import to_minor, currency_decimals
from .http import ProviderError


class Flutterwave:
    """Flutterwave v4 read-only charge and settlement access."""

    SANDBOX_URL = "https://developersandbox-api.flutterwave.com"
    PRODUCTION_URL = "https://f4bexperience.flutterwave.com"

    def __init__(self, environment="sandbox"):
        if environment not in ("sandbox", "production"):
            raise ProviderError("Flutterwave environment must be sandbox or production")
        self.base_url = self.SANDBOX_URL if environment == "sandbox" else self.PRODUCTION_URL
        self.warnings = []

    def _get(self, path, params):
        # Hermes resolves, stores, refreshes and attaches the bearer token. PayOps never receives it.
        from hermes_cli.plugin_provider_requests import credentialed_provider_request

        url = self.base_url.rstrip("/") + "/" + path.lstrip("/")
        if params:
            url += "?" + urlencode(params)
        response = credentialed_provider_request(
            "flutterwave", "GET", url,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "X-Trace-Id": str(uuid4()),
            },
            timeout=20,
        )
        if not 200 <= response.status < 300:
            detail = ""
            try:
                error_payload = response.json()
                parts = []

                def collect_error_text(value):
                    if isinstance(value, dict):
                        for key, item in value.items():
                            if key.lower() in {"code", "error", "error_description", "message", "detail", "title"} and isinstance(item, str):
                                cleaned = " ".join(item.split())
                                if cleaned:
                                    parts.append(cleaned[:120])
                            elif isinstance(item, (dict, list)):
                                collect_error_text(item)
                    elif isinstance(value, list):
                        for item in value[:5]:
                            collect_error_text(item)

                collect_error_text(error_payload)
                detail = "; ".join(dict.fromkeys(parts))[:240]
            except (ValueError, TypeError):
                pass
            suffix = ": " + detail if detail else ""
            raise ProviderError("Flutterwave API returned HTTP %s%s" % (response.status, suffix))
        try:
            payload = response.json()
        except (ValueError, TypeError):
            raise ProviderError("Flutterwave returned invalid JSON") from None
        if not isinstance(payload, dict) or payload.get("status") != "success":
            raise ProviderError("Flutterwave API reported an unsuccessful response")
        rows = payload.get("data")
        if not isinstance(rows, list):
            raise ProviderError("Flutterwave returned an unexpected data shape")
        page_info = (payload.get("meta") or {}).get("page_info")
        if not isinstance(page_info, dict):
            raise ProviderError("Flutterwave response is missing pagination metadata")
        try:
            total_pages = int(page_info["total_pages"])
        except (KeyError, TypeError, ValueError):
            raise ProviderError("Flutterwave response has invalid pagination metadata") from None
        return rows, max(total_pages, 1)

    @staticmethod
    def _range(from_date, to_date):
        # Flutterwave rejects an end timestamp later than the current instant.
        # Keep historical dates inclusive, but cap today/future end dates at now.
        now = datetime.now(timezone.utc)
        today = now.date().isoformat()
        if from_date > today:
            raise ProviderError("Flutterwave date range cannot start in the future")
        end = (
            now.replace(microsecond=0).isoformat().replace("+00:00", "Z")
            if to_date >= today
            else to_date + "T23:59:59Z"
        )
        return {"from": from_date + "T00:00:00Z", "to": end}

    def transactions(self, from_date, to_date, max_pages):
        out = []
        for status in ("succeeded", "pending", "failed", "voided"):
            for page in range(1, max_pages + 1):
                rows, total_pages = self._get("charges", {
                    **self._range(from_date, to_date), "status": status, "page": page, "size": 50,
                })
                for row in rows:
                    currency = str(row.get("currency") or "NGN").upper()
                    out.append(Transaction(
                        provider="flutterwave",
                        transaction_id=str(row.get("id", "")),
                        reference=str(row.get("reference") or ""),
                        amount_minor=to_minor(row.get("amount") or 0, currency_decimals(currency)),
                        currency=currency,
                        status=str(row.get("status") or status).lower(),
                        paid_at=row.get("created_datetime"),
                    ))
                if page >= max_pages and page < total_pages:
                    self.warnings.append(
                        f"transactions ({status}): fetched {page} of {total_pages} pages (max_pages={max_pages})"
                    )
                if page >= total_pages or not rows:
                    break
        return out

    def settlements(self, from_date, to_date, max_pages):
        out = []
        for page in range(1, max_pages + 1):
            rows, total_pages = self._get("settlements", {
                **self._range(from_date, to_date), "page": page, "size": 50,
            })
            for row in rows:
                currency = str(row.get("currency") or "NGN").upper()
                amount = row.get("net_amount")
                if amount is None:
                    amount = row.get("gross_amount") or 0
                out.append(Settlement(
                    provider="flutterwave",
                    settlement_id=str(row.get("id", "")),
                    currency=currency,
                    amount_minor=to_minor(amount, currency_decimals(currency)),
                    status=str(row.get("status") or "unknown").lower(),
                    settled_at=row.get("due_datetime") or row.get("created_datetime"),
                ))
            if page >= max_pages and page < total_pages:
                self.warnings.append(
                    f"settlements: fetched {page} of {total_pages} pages (max_pages={max_pages})"
                )
            if page >= total_pages or not rows:
                break
        return out
