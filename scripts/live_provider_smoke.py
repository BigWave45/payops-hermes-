"""Read-only live smoke test for provider test-mode credentials.

This script never prints transaction identifiers, references, amounts, or credentials.
"""
from datetime import datetime, timedelta, timezone
import os
import sys

from payops.providers import Flutterwave, Paystack


PROVIDERS = {
    "paystack": ("PAYSTACK_TEST_SECRET_KEY", Paystack),
    "flutterwave": ("FLUTTERWAVE_TEST_SECRET_KEY", Flutterwave),
}


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
        requested = list(PROVIDERS)
    if not requested or any(p not in PROVIDERS for p in requested) or len(set(requested)) != len(requested):
        print("Invalid PAYOPS_PROVIDERS selection.", file=sys.stderr)
        return 2

    end = datetime.now(timezone.utc).date()
    start = end - timedelta(days=14)
    from_date, to_date = start.isoformat(), end.isoformat()
    failed = False

    for name in requested:
        secret_name, adapter_type = PROVIDERS[name]
        token = os.environ.get(secret_name)
        if not token:
            print(f"{name}: missing required Actions secret {secret_name}", file=sys.stderr)
            failed = True
            continue
        try:
            adapter = adapter_type(token)
            transactions = adapter.transactions(from_date, to_date, max_pages=2)
            settlements = adapter.settlements(from_date, to_date, max_pages=2)
            validate_records(name, transactions, settlements)
            print(
                f"{name}: authenticated; transactions={len(transactions)}; "
                f"settlements={len(settlements)}; pagination_warnings={len(adapter.warnings)}"
            )
            for warning in adapter.warnings:
                print(f"{name}: warning: {warning}")
        except Exception as exc:
            # Do not print exception messages from arbitrary third-party code.
            print(f"{name}: live smoke test failed ({type(exc).__name__})", file=sys.stderr)
            failed = True

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
