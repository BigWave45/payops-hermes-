"""Read-only Paystack API adapter."""
from .http import get_json, ProviderError
from ..models import Transaction, Settlement

class Paystack:
    base_url = "https://api.paystack.co"

    def __init__(self, token):
        self.token = token

    def _get(self, path, params):
        data = get_json(self.base_url, path, self.token, params)
        if data.get("status") is not True:
            raise ProviderError("Paystack API reported an unsuccessful response")
        return data.get("data") or []

    def transactions(self, from_date, to_date, max_pages):
        out = []
        for page in range(1, max_pages + 1):
            rows = self._get("transaction", {"from": from_date, "to": to_date, "perPage": 100, "page": page})
            for row in rows:
                out.append(Transaction(
                    provider="paystack",
                    transaction_id=str(row.get("id", "")),
                    reference=str(row.get("reference", "")),
                    amount_minor=int(row.get("amount") or 0),
                    currency=str(row.get("currency") or "NGN").upper(),
                    status=str(row.get("status") or "unknown").lower(),
                    paid_at=row.get("paid_at") or row.get("transaction_date"),
                ))
            if len(rows) < 100:
                break
        return out

    def settlements(self, from_date, to_date, max_pages):
        out = []
        for page in range(1, max_pages + 1):
            rows = self._get("settlement", {"from": from_date, "to": to_date, "perPage": 100, "page": page})
            for row in rows:
                amount = row.get("total_amount")
                if amount is None:
                    amount = row.get("amount") or 0
                out.append(Settlement(
                    provider="paystack",
                    settlement_id=str(row.get("id", "")),
                    currency=str(row.get("currency") or "NGN").upper(),
                    amount_minor=int(amount),
                    status=str(row.get("status") or "unknown").lower(),
                    settled_at=row.get("settlement_date") or row.get("createdAt"),
                ))
            if len(rows) < 100:
                break
        return out
