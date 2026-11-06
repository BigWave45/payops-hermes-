"""Hermes tool handlers."""
import json
from datetime import date

from .providers import Paystack, Flutterwave
from .reconcile import build_report


def _get_secret(name):
    # Lazy import keeps pure logic importable outside a Hermes installation.
    from agent.secret_scope import get_secret
    return get_secret(name)


def _validate(args):
    if not isinstance(args, dict):
        raise ValueError("Tool arguments must be an object")
    try:
        start = date.fromisoformat(args["from_date"])
        end = date.fromisoformat(args["to_date"])
    except (KeyError, TypeError, ValueError):
        raise ValueError("from_date and to_date must be valid YYYY-MM-DD dates") from None
    if end < start:
        raise ValueError("to_date must be on or after from_date")
    providers = args.get("providers") or ["paystack", "flutterwave"]
    if not isinstance(providers, list) or not providers or any(p not in ("paystack", "flutterwave") for p in providers):
        raise ValueError("providers must contain paystack and/or flutterwave")
    if len(set(providers)) != len(providers):
        raise ValueError("providers must not contain duplicates")
    pages = args.get("max_pages", 5)
    if isinstance(pages, bool) or not isinstance(pages, int) or not 1 <= pages <= 20:
        raise ValueError("max_pages must be an integer between 1 and 20")
    return start.isoformat(), end.isoformat(), providers, pages


def _collect(args):
    start, end, providers, pages = _validate(args)
    transactions, settlements, errors, warnings = [], [], [], []
    for name in providers:
        try:
            if name == "paystack":
                token = _get_secret("PAYSTACK_SECRET_KEY")
                if not token:
                    errors.append({"provider": name, "error": "API key is not configured in Hermes secret storage"})
                    continue
                adapter = Paystack(token)
            else:
                secret_key = _get_secret("FLUTTERWAVE_SECRET_KEY")
                if not secret_key:
                    errors.append({"provider": name, "error": "Secret key is not configured in Hermes secret storage"})
                    continue
                adapter = Flutterwave(secret_key)
            transactions.extend(adapter.transactions(start, end, pages))
            warning_count = len(getattr(adapter, "warnings", []))
            warnings.extend(f"{name}: {warning}" for warning in adapter.warnings)
            settlements.extend(adapter.settlements(start, end, pages))
            warnings.extend(f"{name}: {warning}" for warning in adapter.warnings[warning_count:])
        except ImportError:
            errors.append({"provider": name, "error": "Hermes secret storage is unavailable in this runtime"})
        except Exception as exc:
            errors.append({"provider": name, "error": str(exc)[:300]})
    return transactions, settlements, errors, warnings


def list_transactions(args: dict, **kwargs) -> str:
    try:
        transactions, _, errors, warnings = _collect(args)
        return json.dumps({
            "transactions": [item.to_dict() for item in transactions],
            "count": len(transactions),
            "provider_errors": errors,
            "provider_warnings": warnings,
        }, ensure_ascii=False)
    except Exception as exc:
        return json.dumps({"error": str(exc)[:300]}, ensure_ascii=False)


def reconcile(args: dict, **kwargs) -> str:
    try:
        transactions, settlements, errors, warnings = _collect(args)
        report = build_report(transactions, settlements)
        report["provider_errors"] = errors
        report["provider_warnings"] = warnings
        report["transaction_count"] = len(transactions)
        report["settlement_count"] = len(settlements)
        return json.dumps(report, ensure_ascii=False)
    except Exception as exc:
        return json.dumps({"error": str(exc)[:300]}, ensure_ascii=False)
