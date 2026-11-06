"""JSON schemas for the public PayOps tools."""
PROVIDERS = {"type": "array", "items": {"type": "string", "enum": ["paystack", "flutterwave"]}, "uniqueItems": True}

DATE_RANGE = {
    "type": "object",
    "properties": {
        "from_date": {"type": "string", "format": "date", "description": "Inclusive start date (YYYY-MM-DD)."},
        "to_date": {"type": "string", "format": "date", "description": "Inclusive end date (YYYY-MM-DD)."},
        "providers": PROVIDERS,
        "max_pages": {"type": "integer", "minimum": 1, "maximum": 20, "default": 5},
    },
    "required": ["from_date", "to_date"],
    "additionalProperties": False,
}

LIST_TRANSACTIONS_SCHEMA = {
    "name": "payops_list_transactions",
    "description": "Read transactions from configured Paystack and/or Flutterwave accounts. No payment actions are performed.",
    "parameters": DATE_RANGE,
}

RECONCILE_SCHEMA = {
    "name": "payops_reconcile",
    "description": "Reconcile provider transaction and settlement records, returning deterministic exceptions and summaries. Read-only.",
    "parameters": DATE_RANGE,
}
