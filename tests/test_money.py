from money import to_minor, from_minor

def test_major_to_minor_rounding():
    assert to_minor("123.45") == 12345

def test_minor_to_major():
    assert from_minor(12345) == "123.45"
