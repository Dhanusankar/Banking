"""
agent.py

Rule-based agent that converts a natural language string into an API call
description (method/url/params/json) used by the orchestrator. Kept simple
for the POC.
"""
from typing import Dict, Any

from intent_classifier import classify_intent
from transfer_extractor import extract_transfer_details


def build_api_call(message: str) -> Dict[str, Any]:
    intent = classify_intent(message)

    if intent == "balance_inquiry":
        return {
            "intent": "balance_inquiry",
            "method": "GET",
            "url": "http://localhost:8080/api/balance",
            "params": {"accountId": "123"}
        }

    if intent == "money_transfer":
        details = extract_transfer_details(message)
        if not details:
            return {"intent": "money_transfer", "error": "Could not parse transfer details"}

        to_account = details.get("recipient", "kiran").lower()
        amount = details.get("amount")

        return {
            "intent": "money_transfer",
            "method": "POST",
            "url": "http://localhost:8080/api/transfer",
            "json": {
                "fromAccount": "123",
                "toAccount": to_account,
                "amount": amount
            }
        }

    return {"intent": "fallback", "message": "Sorry, I don't understand."}


if __name__ == "__main__":
    print(build_api_call("What's my balance?"))
    print(build_api_call("Transfer 2000 to Kiran."))
