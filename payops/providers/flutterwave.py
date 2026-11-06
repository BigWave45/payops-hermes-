"""Read-only Flutterwave v4 sandbox API adapter."""
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from .http import get_json, post_form_json, ProviderError
from ..models import Transaction, Settlement
from ..money import to_minor, currency_decimals

TOKEN_URL = "https://idp.flutterwave.com/realms/flutterwave/protocol/openid-connect/token"


class Flutterwave:
    base_url = "https://developersandbox-api.flutterwave.com"

    def __init__(self, client_id, client_secret):
        if not client_id or not client_secret:
            raise ProviderError("Flutterwave v4 client credentials are not configured")
        token_response = post_form_json(TOKEN_URL, {
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": "client_credentials",
        })
        token = token_response.get("access_token")
        if not isinstance(token, str) or not token:
            raise ProviderError("Flutterwave OAuth response did not contain an access token")
        self.token = token
        self.warnings = []

    def _get(self, path, params):
        response = get_json(
            self.base_url,
            path,
            self.token,
            params,
            headers={"X-Trace-Id": str(uuid4())},
        )
        if response.get("status") != "success":
            raise ProviderError("Flutterwave API reported an unsuccessful response")
        rows = response.get("data")
        if not isinstance(rows, list):
            raise ProviderError("Flutterwave returned an unexpected data shape")
        page_info = (response.get("meta") or {}).get("page_info")
        if not isinstance(page_info, dict):
            raise ProviderError("Flutterwave response is missing pagination metadata")
        try:
            total_pages = int(page_info["total_pages"])
        except (KeyError, TypeError, ValueError):
            raise ProviderError("Flutterwave response has invalid pagination metadata") from None
        return rows, max(total_pages, 1)

    def transactions(self, from_date, to_date, max_pages):
        out = []
        # Flutterwave rejects an upper bound later than the current instant.
        start_dt = datetime.strptime(from_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        requested_end = (
            datetime.strptime(to_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            + timedelta(days=1)
            - timedelta(seconds=1)
        )
        end_dt = min(requested_end, datetime.now(timezone.utc)).replace(microsecond=0)
        if end_dt < start_dt:
            return out

        # v4 exposes collected payments through the read-only charges collection.
        # Pending, succeeded, failed and voided are requested separately so that
        # the result is not silently restricted to successful charges.
        for status in ("succeeded", "pending", "failed", "voided"):
            for page in range(1, max_pages + 1):
                rows, total_pages = self._get("charges", {
                    "from": start_dt.isoformat().replace("+00:00", "Z"),
                    "to": end_dt.isoformat().replace("+00:00", "Z"),
                    "status": status,
                    "page": page,
                    "size": 50,
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
        start_dt = datetime.strptime(from_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        requested_end = (
            datetime.strptime(to_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            + timedelta(days=1)
            - timedelta(seconds=1)
        )
        end_dt = min(requested_end, datetime.now(timezone.utc)).replace(microsecond=0)
        if end_dt < start_dt:
            return out

        # The v4 settlements endpoint requires ISO 8601 date-time values,
        # unlike legacy v3 endpoints that accept YYYY-MM-DD.
        from_value = start_dt.isoformat().replace("+00:00", "Z")
        to_value = end_dt.isoformat().replace("+00:00", "Z")
        for page in range(1, max_pages + 1):
            rows, total_pages = self._get("settlements", {
                "from": from_value,
                "to": to_value,
                "page": page,
                "size": 50,
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
                    settled_at=row.get("created_datetime") or row.get("due_datetime"),
                ))
            if page >= max_pages and page < total_pages:
                self.warnings.append(
                    f"settlements: fetched {page} of {total_pages} pages (max_pages={max_pages})"
                )
            if page >= total_pages or not rows:
                break
        return out
