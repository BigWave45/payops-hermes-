"""Currency-safe minor-unit helpers."""
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

def to_minor(amount, decimals=2):
    try:
        value = Decimal(str(amount))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError("Invalid monetary amount") from exc
    if not value.is_finite():
        raise ValueError("Monetary amount must be finite")
    factor = Decimal(10) ** decimals
    return int((value * factor).quantize(Decimal("1"), rounding=ROUND_HALF_UP))

def from_minor(amount, decimals=2):
    return str(Decimal(int(amount)) / (Decimal(10) ** decimals))
