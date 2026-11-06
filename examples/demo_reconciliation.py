"""Deterministic demonstration using synthetic records; no provider API is called."""
import json

from payops.models import Settlement, Transaction
from payops.reconcile import build_report


def main():
    transactions = [
        Transaction("paystack", "txn_1001", "order-100", 500000, "NGN", "success"),
        Transaction("paystack", "txn_1002", "order-101", 250000, "NGN", "success"),
        # Deliberate duplicate reference to demonstrate the data-quality exception.
        Transaction("paystack", "txn_1003", "order-100", 500000, "NGN", "success"),
        Transaction("paystack", "txn_1004", "order-102", 10000, "NGN", "failed"),
    ]
    settlements = [
        Settlement("paystack", "settlement_01", "NGN", 720000, "settled"),
    ]

    report = build_report(transactions, settlements)
    report["demo_notice"] = (
        "SYNTHETIC FIXTURE DATA. These records are illustrative and were not retrieved "
        "from a merchant account. Transaction and settlement totals are reported "
        "separately and are not asserted to be directly equivalent."
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
