"""
Extract transfer amount and recipient using simple regex rules.
"""
import re
from typing import Optional, Dict

AMOUNT_RE = re.compile(r"\b(\d+(?:[\.,]\d{1,2})?)\b")
RECIPIENT_RE = re.compile(r"to\s+(\w+)", re.IGNORECASE)


def extract_transfer_details(message: str) -> Optional[Dict[str, any]]:
    m = message.lower()
    amount_match = AMOUNT_RE.search(m)
    recipient_match = RECIPIENT_RE.search(message)

    if not amount_match:
        return None

    amount_str = amount_match.group(1).replace(',', '.')
    try:
        amount = float(amount_str)
    except ValueError:
        return None

    recipient = recipient_match.group(1) if recipient_match else 'kiran'
    return {"amount": amount, "recipient": recipient}
