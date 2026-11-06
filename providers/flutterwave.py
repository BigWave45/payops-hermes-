"""Read-only Flutterwave v3 API adapter."""
from .http import get_json, ProviderError
from ..models import Transaction, Settlement
from ..money import to_minor

class Flutterwave:
    base_url = "https://api.flutterwave.com/v3"

    def __init__(self, token):
        self.token = token

    def _get(self, path, params):
        data = get_json(self.base_url, path, self.token, params)
        if data.get("status") != "success":
            raise ProviderError("Flutterwave API reported an unsuccessful response")
        return data.get("data") or []

    def transactions(self, from_date, to_date, max_pages):
        out = []
        # v3 list endpoint exposes successful/failed filters; pending states may be absent.
        for status in ("successful", "failed"):
            for page in range(1, max_pages + 1):
                rows = self._get("transactions", {
                    "from": from_date, "to": to_date, "status": status,
                    "page": page, "size": 100,
                })
                for row in rows:
                    out.append(Transaction(
                        provider="flutterwave",
                        transaction_id=str(row.get("id", "")),
                        reference=str(row.get("tx_ref") or row.get("flw_ref") or ""),
                        amount_minor=to_minor(row.get("amount") or 0),
                        currency=str(row.get("currency") or "NGN").upper(),
                        status=str(row.get("status") or status).lower(),
                        paid_at=row.get("created_at") or row.get("charged_at"),
                    ))
                if len(rows) < 100:
                    break
        return out

    def settlements(self, from_date, to_date, max_pages):
        out = []
        for page in range(1, max_pages + 1):
            rows = self._get("settlements", {"from": from_date, "to": to_date, "page": page, "size": 100})
            for row in rows:
                out.append(Settlement(
                    provider="flutterwave",
                    settlement_id=str(row.get("id", "")),
                    currency=str(row.get("currency") or "NGN").upper(),
                    amount_minor=to_minor(row.get("amount") or row.get("net_amount") or 0),
                    status=str(row.get("status") or "unknown").lower(),
                    settled_at=row.get("created_at") or row.get("settlement_date"),
                ))
            if len(rows) < 100:
                break
        return out
