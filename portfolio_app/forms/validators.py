"""Custom validators for form validation."""

from decimal import Decimal, InvalidOperation
from typing import Optional, Tuple


def parse_decimal_field(
    value: str,
    *,
    allow_blank: bool = False
) -> Tuple[Optional[Decimal], Optional[str]]:
    """Parse a decimal field from form input.

    Args:
        value: The string value to parse
        allow_blank: Whether to allow blank values

    Returns:
        Tuple of (decimal_value, error_message)
        If successful: (Decimal, None)
        If error: (None, error_message)
    """
    v = (value or '').strip()
    if v == '':
        return (None, None) if allow_blank else (None, 'Required.')
    try:
        return Decimal(v), None
    except (InvalidOperation, ValueError, TypeError):
        return None, 'Invalid number.'


def validate_positive_decimal(
    value: str,
    *,
    allow_zero: bool = False,
    allow_blank: bool = False
) -> Tuple[Optional[Decimal], Optional[str]]:
    """Validate that a decimal field is positive.

    Args:
        value: The string value to validate
        allow_zero: Whether to allow zero values
        allow_blank: Whether to allow blank values

    Returns:
        Tuple of (decimal_value, error_message)
    """
    dec, err = parse_decimal_field(value, allow_blank=allow_blank)
    if err:
        return None, err
    if dec is None:
        return None, None
    if allow_zero:
        if dec < 0:
            return None, 'Non-negative number required.'
        return dec, None
    if dec <= 0:
        return None, 'Value must be greater than 0.'
    return dec, None



def get_field_error_message(field_name: str, base_msg: str = 'Value must be greater than 0.') -> str:
    """Get field-specific error message.

    Args:
        field_name: Name of the field
        base_msg: Base error message

    Returns:
        Field-specific error message
    """
    if field_name in ('price', 'edit_price'):
        return 'Price must be greater than 0.'
    if field_name in ('quantity', 'edit_quantity'):
        return 'Quantity must be greater than 0.'
    if field_name in ('amount', 'amount_delta', 'edit_event_amount'):
        return 'Amount must be greater than 0.'
    return base_msg
