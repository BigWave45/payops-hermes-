from payops.models import Transaction, Settlement
from payops.reconcile import build_report

def test_duplicate_reference_scoped_to_provider():
    txs = [
        Transaction("paystack", "1", "same", 100, "NGN", "success"),
        Transaction("paystack", "2", "same", 200, "NGN", "success"),
        Transaction("flutterwave", "3", "same", 300, "NGN", "successful"),
    ]
    report = build_report(txs, [])
    assert len(report["exceptions"]) == 1
    assert report["exceptions"][0]["type"] == "duplicate_reference"

def test_transaction_and_settlement_totals_are_separate():
    txs = [Transaction("paystack", "1", "ref", 10000, "NGN", "success")]
    sts = [Settlement("paystack", "s1", "NGN", 8000, "settled")]
    report = build_report(txs, sts)
    assert report["transaction_summaries"][0]["transaction_amount_minor"] == 10000
    assert report["settlement_summaries"][0]["settled_amount_minor"] == 8000
    assert "exceptions" in report

def test_flutterwave_succeeded_status_counts_toward_successful_total():
    txs = [
        Transaction("flutterwave", "1", "fw_1", 12500, "NGN", "succeeded"),
        Transaction("flutterwave", "2", "fw_2", 500, "NGN", "pending"),
        Transaction("flutterwave", "3", "fw_3", 250, "NGN", "failed"),
        Transaction("flutterwave", "4", "fw_4", 100, "NGN", "voided"),
    ]
    report = build_report(txs, [])
    summary = report["transaction_summaries"][0]
    assert summary["transaction_count"] == 4
    assert summary["successful_count"] == 1
    assert summary["failed_count"] == 1
    assert summary["transaction_amount_minor"] == 12500

