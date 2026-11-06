"""Read-only live smoke test for provider test-mode credentials.

This script never prints transaction identifiers, references, amounts, or credentials.
"""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import os
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from payops.providers import Flutterwave, Paystack
from payops.providers.http import ProviderError


def validate_records(provider, transactions, settlements):
    for item in transactions:
        if item.provider != provider or not item.transaction_id:
            raise ValueError("transaction identity normalization failed")
        if not isinstance(item.amount_minor, int) or len(item.currency) != 3:
            raise ValueError("transaction amount/currency normalization failed")
    for item in settlements:
        if item.provider != provider or not item.settlement_id:
            raise ValueError("settlement identity normalization failed")
        if not isinstance(item.amount_minor, int) or len(item.currency) != 3:
            raise ValueError("settlement amount/currency normalization failed")


def main():
    requested = [p.strip() for p in os.environ.get("PAYOPS_PROVIDERS", "both").split(",")]
    if requested == ["both"]:
        requested = ["paystack", "flutterwave"]
    if not requested or any(p not in ("paystack", "flutterwave") for p in requested) or len(set(requested)) != len(requested):
        print("Invalid PAYOPS_PROVIDERS selection.", file=sys.stderr)
        return 2

    end = datetime.now(timezone.utc).date()
    start = end - timedelta(days=14)
    from_date, to_date = start.isoformat(), end.isoformat()
    failed = False

    for name in requested:
        stage = "initialization"
        try:
            if name == "paystack":
                token = os.environ.get("PAYSTACK_TEST_SECRET_KEY")
                if not token:
                    raise ProviderError("missing required Actions secret PAYSTACK_TEST_SECRET_KEY")
                adapter = Paystack(token)
            else:
                client_id = os.environ.get("FLUTTERWAVE_CLIENT_ID")
                client_secret = os.environ.get("FLUTTERWAVE_CLIENT_SECRET")
                if not client_id or not client_secret:
                    raise ProviderError("missing required Actions secrets FLUTTERWAVE_CLIENT_ID and FLUTTERWAVE_CLIENT_SECRET")
                adapter = Flutterwave(client_id, client_secret)

            stage = "transaction listing"
            transactions = adapter.transactions(from_date, to_date, max_pages=2)
            stage = "settlement listing"
            settlements = adapter.settlements(from_date, to_date, max_pages=2)
            stage = "normalized record validation"
            validate_records(name, transactions, settlements)
            print(
                f"{name}: success; transactions={len(transactions)}; "
                f"settlements={len(settlements)}; pagination_warnings={len(adapter.warnings)}"
            )
            for warning in adapter.warnings:
                print(f"{name}: warning: {warning}")
            if name == "flutterwave":
                print("flutterwave: note: sandbox settlement data is not expected; settlements require eligible live transactions")
        except ProviderError as exc:
            print(f"{name}: {stage} failed ({exc})", file=sys.stderr)
            failed = True
        except Exception as exc:
            print(f"{name}: {stage} failed ({type(exc).__name__})", file=sys.stderr)
            failed = True

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
