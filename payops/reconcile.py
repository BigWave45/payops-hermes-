"""Deterministic reconciliation; does not assume settlement and transaction windows match."""
from collections import Counter, defaultdict

def build_report(transactions, settlements):
    exceptions = []
    seen = set()
    summaries = defaultdict(lambda: {"transaction_count": 0, "successful_count": 0, "failed_count": 0, "transaction_amount_minor": 0})
    for tx in transactions:
        key = (tx.provider, tx.reference)
        if tx.reference and key in seen:
            exceptions.append({"type": "duplicate_reference", "provider": tx.provider, "reference": tx.reference})
        seen.add(key)
        item = summaries[(tx.provider, tx.currency)]
        item["transaction_count"] += 1
        if tx.status in ("success", "successful", "succeeded"):
            item["successful_count"] += 1
            item["transaction_amount_minor"] += tx.amount_minor
        elif tx.status in ("failed", "failure"):
            item["failed_count"] += 1

    settlement_summaries = defaultdict(lambda: {"settlement_count": 0, "settled_amount_minor": 0, "non_final_count": 0})
    for st in settlements:
        item = settlement_summaries[(st.provider, st.currency)]
        item["settlement_count"] += 1
        if st.status in ("success", "successful", "settled", "completed"):
            item["settled_amount_minor"] += st.amount_minor
        else:
            item["non_final_count"] += 1

    return {
        "transaction_summaries": [
            {"provider": k[0], "currency": k[1], **v} for k, v in sorted(summaries.items())
        ],
        "settlement_summaries": [
            {"provider": k[0], "currency": k[1], **v} for k, v in sorted(settlement_summaries.items())
        ],
        "exceptions": exceptions,
        "limitations": [
            "Transaction totals and settlement totals are reported separately; settlement timing can lag transaction activity.",
            "Duplicate references are detected only within the same provider.",
            "Flutterwave v4 charge listing queries succeeded, pending, failed, and voided statuses.",
            "This report does not establish bank-statement or merchant-order-ledger equivalence."
        ],
    }
