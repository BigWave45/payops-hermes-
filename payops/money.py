"""Currency-aware conversion to integer minor units."""
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

_ZERO_DECIMAL = {"BIF", "CLP", "DJF", "GNF", "ISK", "JPY", "KMF", "KRW", "PYG", "RWF", "UGX", "VND", "VUV", "XAF", "XOF", "XPF"}
_THREE_DECIMAL = {"BHD", "IQD", "JOD", "KWD", "LYD", "OMR", "TND"}

def currency_decimals(currency):
    code = str(currency).upper()
    if len(code) != 3 or not code.isalpha():
        raise ValueError("Invalid ISO currency code")
    if code in _ZERO_DECIMAL:
        return 0
    if code in _THREE_DECIMAL:
        return 3
    return 2

def to_minor(amount, decimals=2):
    try:
        value = Decimal(str(amount))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError("Invalid monetary amount") from exc
    if not value.is_finite():
        raise ValueError("Monetary amount must be finite")
    if isinstance(decimals, bool) or not isinstance(decimals, int) or not 0 <= decimals <= 4:
        raise ValueError("Currency decimal precision must be an integer from 0 to 4")
    factor = Decimal(10) ** decimals
    return int((value * factor).quantize(Decimal("1"), rounding=ROUND_HALF_UP))

def from_minor(amount, decimals=2):
    return str(Decimal(int(amount)) / (Decimal(10) ** decimals))
