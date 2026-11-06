"""Read-only Flutterwave v3 API adapter."""
from .http import get_json, ProviderError
from ..models import Transaction, Settlement
from ..money import to_minor, currency_decimals


class Flutterwave:
    base_url = "https://api.flutterwave.com/v3"

    def __init__(self, token):
        self.token = token

    def _get(self, path, params):
        response = get_json(self.base_url, path, self.token, params)
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
        if total_pages < 1:
            total_pages = 1
        return rows, total_pages

    def transactions(self, from_date, to_date, max_pages):
        out = []
        # v3 list endpoint exposes successful/failed filters; pending states may be absent.
        for status in ("successful", "failed"):
            for page in range(1, max_pages + 1):
                rows, total_pages = self._get("transactions", {
                    "from": from_date, "to": to_date, "status": status, "page": page,
                })
                for row in rows:
                    currency = str(row.get("currency") or "NGN").upper()
                    out.append(Transaction(
                        provider="flutterwave",
                        transaction_id=str(row.get("id", "")),
                        reference=str(row.get("tx_ref") or row.get("flw_ref") or ""),
                        amount_minor=to_minor(row.get("amount") or 0, currency_decimals(currency)),
                        currency=currency,
                        status=str(row.get("status") or status).lower(),
                        paid_at=row.get("created_at") or row.get("charged_at"),
                    ))
                if page >= total_pages or not rows:
                    break
        return out

    def settlements(self, from_date, to_date, max_pages):
        out = []
        for page in range(1, max_pages + 1):
            rows, total_pages = self._get("settlements", {
                "from": from_date, "to": to_date, "page": page,
            })
            for row in rows:
                currency = str(row.get("currency") or "NGN").upper()
                amount = row.get("amount")
                if amount is None:
                    amount = row.get("net_amount") or 0
                out.append(Settlement(
                    provider="flutterwave",
                    settlement_id=str(row.get("id", "")),
                    currency=currency,
                    amount_minor=to_minor(amount, currency_decimals(currency)),
                    status=str(row.get("status") or "unknown").lower(),
                    settled_at=row.get("created_at") or row.get("settlement_date"),
                ))
            if page >= total_pages or not rows:
                break
        return out
