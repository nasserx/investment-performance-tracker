"""Concise user-facing messages for the application."""


class ErrorMessages:
    """Concise error messages."""

    INVALID_QUANTITY = "Invalid quantity"
    INVALID_PRICE = "Invalid price"
    INVALID_AMOUNT = "Invalid amount"
    INVALID_DATE = "Invalid date"
    TRANSACTION_NOT_FOUND = "Transaction not found"
    FUND_NOT_FOUND = "Fund not found"
    INVALID_FUND = "Invalid fund"
    REQUIRED_FIELD = "Required field"
    INVALID_INPUT = "Invalid input"
    INVALID_SYMBOL = "Invalid symbol"
    OPERATION_FAILED = "Operation failed"


class SuccessMessages:
    """Concise success messages."""

    # Transaction messages
    TRANSACTION_ADDED = "Transaction added"
    TRANSACTION_UPDATED = "Transaction updated"
    TRANSACTION_DELETED = "Transaction deleted"

    # Fund messages
    FUND_CREATED = "Fund created"
    FUND_UPDATED = "Fund updated"
    FUND_DELETED = "Fund deleted"
    DEPOSIT_COMPLETED = "Deposit completed"
    WITHDRAWAL_COMPLETED = "Withdrawal completed"

    # Asset messages
    ASSET_ADDED = "Asset added"
    ASSET_DELETED = "Asset deleted"

    # Event messages
    EVENT_UPDATED = "Event updated"
    EVENT_DELETED = "Event deleted"


class ConfirmMessages:
    """Confirmation messages."""

    DELETE_TRANSACTION = "Delete this transaction?"
    DELETE_FUND = "Delete this fund?"
    DELETE_ASSET = "Delete this asset?"
    DELETE_EVENT = "Delete this event?"


def get_error_message(exception):
    """Convert exception to concise user-facing message.

    Args:
        exception: The exception object

    Returns:
        str: Concise error message
    """
    exception_msg = str(exception).lower()

    if 'quantity' in exception_msg and ('invalid' in exception_msg or 'must be' in exception_msg):
        return ErrorMessages.INVALID_QUANTITY
    elif 'price' in exception_msg and ('invalid' in exception_msg or 'must be' in exception_msg):
        return ErrorMessages.INVALID_PRICE
    elif 'amount' in exception_msg and ('invalid' in exception_msg or 'must be' in exception_msg):
        return ErrorMessages.INVALID_AMOUNT
    elif 'date' in exception_msg and 'invalid' in exception_msg:
        return ErrorMessages.INVALID_DATE
    elif 'not found' in exception_msg and 'transaction' in exception_msg:
        return ErrorMessages.TRANSACTION_NOT_FOUND
    elif 'not found' in exception_msg and 'fund' in exception_msg:
        return ErrorMessages.FUND_NOT_FOUND
    elif 'symbol' in exception_msg and 'invalid' in exception_msg:
        return ErrorMessages.INVALID_SYMBOL
    else:
        # Return first line of error message if it's short, otherwise generic
        first_line = str(exception).split('\n')[0].strip()
        if len(first_line) <= 50:
            return first_line
        return ErrorMessages.OPERATION_FAILED


def get_first_form_error(form_errors):
    """Extract first error message from form errors dict.

    Args:
        form_errors: Dictionary of form errors (field: error_message)

    Returns:
        str: First error message, or 'Invalid input' if no errors
    """
    if not form_errors:
        return 'Invalid input'

    # Get first error value
    first_error = next(iter(form_errors.values()))

    # Handle both list and string error formats
    if isinstance(first_error, list):
        return first_error[0] if first_error else 'Invalid input'
    else:
        return str(first_error)
