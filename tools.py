"""Hermes tool handlers."""
import json
from datetime import date
from agent.secret_scope import get_secret
from .providers import Paystack, Flutterwave
from .reconcile import build_report

def _validate(args):
    start = date.fromisoformat(args["from_date"])
    end = date.fromisoformat(args["to_date"])
    if end < start:
        raise ValueError("to_date must be on or after from_date")
    providers = args.get("providers") or ["paystack", "flutterwave"]
    if not providers or any(p not in ("paystack", "flutterwave") for p in providers):
        raise ValueError("providers must contain paystack and/or flutterwave")
    pages = int(args.get("max_pages", 5))
    if not 1 <= pages <= 20:
        raise ValueError("max_pages must be between 1 and 20")
    return start.isoformat(), end.isoformat(), providers, pages

def _collect(args):
    start, end, providers, pages = _validate(args)
    transactions, settlements, errors = [], [], []
    for name in providers:
        try:
            key_name = "PAYSTACK_SECRET_KEY" if name == "paystack" else "FLUTTERWAVE_SECRET_KEY"
            token = get_secret(key_name)
            if not token:
                errors.append({"provider": name, "error": "API key is not configured in Hermes secret storage"})
                continue
            adapter = Paystack(token) if name == "paystack" else Flutterwave(token)
            transactions.extend(adapter.transactions(start, end, pages))
            settlements.extend(adapter.settlements(start, end, pages))
        except Exception as exc:
            errors.append({"provider": name, "error": str(exc)[:300]})
    return transactions, settlements, errors

def list_transactions(args):
    transactions, _, errors = _collect(args)
    return json.dumps({
        "transactions": [item.to_dict() for item in transactions],
        "count": len(transactions),
        "provider_errors": errors,
    }, ensure_ascii=False)

def reconcile(args):
    transactions, settlements, errors = _collect(args)
    report = build_report(transactions, settlements)
    report["provider_errors"] = errors
    report["transaction_count"] = len(transactions)
    report["settlement_count"] = len(settlements)
    return json.dumps(report, ensure_ascii=False)
