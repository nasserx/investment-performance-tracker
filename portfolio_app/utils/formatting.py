"""Formatting utilities for decimal and money values."""

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


def fmt_decimal(value):
    """Format a number like user input: no forced decimals + thousands separators.

    - Avoid scientific notation
    - Trim trailing zeros
    - Add commas to the integer part
    """
    if value is None:
        return ''

    # Keep Decimals intact; convert others via str() to avoid float artifacts.
    try:
        d = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return str(value)

    # Fixed-point string (no exponent).
    s = format(d, 'f')
    sign = ''
    if s.startswith('-'):
        sign = '-'
        s = s[1:]

    if '.' in s:
        int_part, frac_part = s.split('.', 1)
        frac_part = frac_part.rstrip('0')
    else:
        int_part, frac_part = s, ''

    # Add thousands separators.
    if int_part:
        int_part = f"{int(int_part):,}"
    else:
        int_part = '0'

    if frac_part:
        return f"{sign}{int_part}.{frac_part}"
    return f"{sign}{int_part}"


def fmt_money(value, decimals=2):
    """Format a number as money: thousands separators + fixed decimals.

    - Avoid scientific notation
    - Round using ROUND_HALF_UP (finance-friendly)
    - Add commas to the integer part
    """
    if value is None:
        return ''

    try:
        d = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return str(value)

    try:
        decimals_int = int(decimals)
    except (ValueError, TypeError):
        decimals_int = 2

    # Guard rails to avoid pathological formats.
    decimals_int = max(0, min(decimals_int, 12))

    quant = Decimal('1').scaleb(-decimals_int)  # 10**(-decimals)
    try:
        d = d.quantize(quant, rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError):
        # Fallback: best-effort string format.
        return format(d, 'f')

    return format(d, f",.{decimals_int}f")
