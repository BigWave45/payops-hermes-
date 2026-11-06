from money import to_minor, from_minor, currency_decimals

def test_major_to_minor_rounding():
    assert to_minor("123.45") == 12345

def test_minor_to_major():
    assert from_minor(12345) == "123.45"

def test_zero_decimal_currency():
    assert currency_decimals("JPY") == 0
    assert to_minor("125", currency_decimals("JPY")) == 125

def test_three_decimal_currency():
    assert currency_decimals("KWD") == 3
    assert to_minor("1.234", currency_decimals("KWD")) == 1234
