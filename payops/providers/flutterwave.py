"""Read-only Flutterwave v3 API adapter using Hermes-managed secret storage."""
from ..models import Transaction, Settlement
from ..money import to_minor, currency_decimals
from .http import get_json, ProviderError


class Flutterwave:
    """Flutterwave v3 read-only transaction and settlement access."""

    base_url = "https://api.flutterwave.com"

    def __init__(self, secret_key):
        if not isinstance(secret_key, str) or not secret_key.strip():
            raise ProviderError("Flutterwave secret key is not configured")
        self.token = secret_key.strip()
        self.warnings = [
            "transactions: Flutterwave v3 list endpoint exposes successful and failed statuses; pending transactions are not included"
        ]

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
        return rows, max(total_pages, 1)

    def transactions(self, from_date, to_date, max_pages):
        out = []
        # v3 exposes successful and failed transactions through this list endpoint.
        for status in ("successful", "failed"):
            for page in range(1, max_pages + 1):
                rows, total_pages = self._get("v3/transactions", {
                    "from": from_date,
                    "to": to_date,
                    "status": status,
                    "page": page,
                })
                for row in rows:
                    currency = str(row.get("currency") or "NGN").upper()
                    amount = row.get("charged_amount")
                    if amount is None:
                        amount = row.get("amount") or 0
                    out.append(Transaction(
                        provider="flutterwave",
                        transaction_id=str(row.get("id", "")),
                        reference=str(row.get("tx_ref") or row.get("flw_ref") or ""),
                        amount_minor=to_minor(amount, currency_decimals(currency)),
                        currency=currency,
                        status=str(row.get("status") or status).lower(),
                        paid_at=row.get("created_at") or row.get("transaction_date"),
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
            rows, total_pages = self._get("v3/settlements", {
                "from": from_date,
                "to": to_date,
                "page": page,
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
                    settled_at=row.get("processed_date") or row.get("created_at"),
                ))
            if page >= max_pages and page < total_pages:
                self.warnings.append(
                    f"settlements: fetched {page} of {total_pages} pages (max_pages={max_pages})"
                )
            if page >= total_pages or not rows:
                break
        return out
