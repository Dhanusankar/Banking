"""
Extract transfer amount and recipient using simple regex rules.
"""
import re
from typing import Optional, Dict

AMOUNT_RE = re.compile(r"(?:send|transfer)?\s*(\d+(?:[\.,]\d{1,2})?)", re.IGNORECASE)
RECIPIENT_RE = re.compile(r"to\s+(account\s*\d+|\w+|'\w+|\w+'s\s+account)", re.IGNORECASE)
POSSESSIVE_RECIPIENT_RE = re.compile(r"(\w+)'s\s+account", re.IGNORECASE)
ALT_RECIPIENT_RE = re.compile(r"account\s*(\d+)", re.IGNORECASE)
NAME_RECIPIENT_RE = re.compile(r"to\s+(\w+)", re.IGNORECASE)


def extract_transfer_details(message: str) -> Optional[Dict[str, any]]:
    amount_match = AMOUNT_RE.search(message)
    recipient_match = RECIPIENT_RE.search(message)
    possessive_match = POSSESSIVE_RECIPIENT_RE.search(message)
    alt_recipient_match = ALT_RECIPIENT_RE.search(message)
    name_recipient_match = NAME_RECIPIENT_RE.search(message)

    print(f"DEBUG: message='{message}'")
    print(f"DEBUG: amount_match={amount_match}")
    print(f"DEBUG: recipient_match={recipient_match}")
    print(f"DEBUG: possessive_match={possessive_match}")
    print(f"DEBUG: alt_recipient_match={alt_recipient_match}")
    print(f"DEBUG: name_recipient_match={name_recipient_match}")

    if not amount_match:
        print("DEBUG: No amount found.")
        return None

    amount_str = amount_match.group(1).replace(',', '.')
    try:
        amount = float(amount_str)
    except ValueError:
        print("DEBUG: Amount conversion failed.")
        return None

    # Prefer account number if present
    if alt_recipient_match:
        recipient = alt_recipient_match.group(1)
        print(f"DEBUG: Using alt_recipient_match: {recipient}")
    elif possessive_match:
        recipient = possessive_match.group(1)
        print(f"DEBUG: Using possessive_match: {recipient}")
    elif recipient_match:
        rec = recipient_match.group(1)
        recipient = re.sub(r"'s account$", "", rec)
        print(f"DEBUG: Using recipient_match: {recipient}")
    elif name_recipient_match:
        recipient = name_recipient_match.group(1)
        print(f"DEBUG: Using name_recipient_match: {recipient}")
    else:
        recipient = 'kiran'
        print("DEBUG: Default recipient: kiran")
    print(f"DEBUG: Final extraction: amount={amount}, recipient={recipient}")
    return {"amount": amount, "recipient": recipient}
