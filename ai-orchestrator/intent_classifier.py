"""Simple rule-based intent classifier."""

def classify_intent(message: str) -> str:
    m = message.lower()
    if "balance" in m or "what's my balance" in m or "what is my balance" in m:
        return "balance_inquiry"
    if "transfer" in m or "send" in m or "pay" in m:
        return "money_transfer"
    return "fallback"
