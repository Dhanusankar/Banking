"""
LLM-powered intent classifier using Llama-3 via Ollama.
Replaces rule-based classification with intelligent NLU.
"""
import requests
import json
import re
from typing import Dict, Tuple


OLLAMA_API_URL = "http://localhost:11434/api/generate"
LLAMA_MODEL = "llama3"


def classify_intent_with_llm(message: str) -> Tuple[str, Dict, float]:
    """
    Use Llama-3 to classify user intent and extract entities.
    
    Args:
        message: User's natural language request
        
    Returns:
        Tuple of (intent, entities, confidence)
        - intent: balance_inquiry, money_transfer, account_statement, loan_inquiry, fallback
        - entities: dict with extracted information
        - confidence: float 0.0-1.0
    """
    # Construct prompt for Llama-3
    prompt = f"""You are a banking AI assistant that analyzes customer requests.

User Request: "{message}"

Analyze this banking request and respond ONLY with valid JSON in this exact format:
{{
    "intent": "one of: balance_inquiry, money_transfer, account_statement, loan_inquiry, fallback",
    "entities": {{
        "amount": null or number (for transfers),
        "recipient": null or string (for transfers),
        "account": "123" (default account)
    }},
    "confidence": 0.95,
    "reasoning": "Brief explanation"
}}

Intent Definitions:
- balance_inquiry: User wants to check account balance
- money_transfer: User wants to transfer/send/pay money
- account_statement: User wants transaction history/statement
- loan_inquiry: User wants loan information/eligibility
- fallback: Unclear or non-banking request

Rules:
1. confidence should be 0.90+ for clear requests
2. confidence should be 0.50-0.80 for vague requests
3. confidence should be <0.50 for unclear/non-banking requests
4. Extract amount as number (not string) for transfers
5. Handle typos gracefully (e.g., "tansfer" = "transfer")

Respond with ONLY the JSON, no explanation:"""

    try:
        response = requests.post(
            OLLAMA_API_URL,
            json={
                "model": LLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "format": "json"
            },
            timeout=30
        )
        response.raise_for_status()
        
        # Parse Ollama response
        ollama_data = response.json()
        llm_response = ollama_data.get("response", "")
        
        # Extract JSON from response
        json_match = re.search(r'\{.*\}', llm_response, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group(0))
        else:
            result = json.loads(llm_response)
        
        # Extract values
        intent = result.get("intent", "fallback")
        entities = result.get("entities", {})
        confidence = float(result.get("confidence", 0.5))
        
        # Validate intent
        valid_intents = [
            "balance_inquiry", 
            "money_transfer", 
            "account_statement", 
            "loan_inquiry", 
            "fallback"
        ]
        if intent not in valid_intents:
            intent = "fallback"
            confidence = 0.3
        
        print(f"🤖 LLM Classification: intent={intent}, confidence={confidence:.2f}")
        print(f"   Entities: {entities}")
        
        return intent, entities, confidence
        
    except Exception as e:
        print(f"⚠️ LLM classification error: {e}")
        # Fallback to simple rule-based
        return fallback_classify(message)


def fallback_classify(message: str) -> Tuple[str, Dict, float]:
    """
    Fallback to simple rule-based classification if LLM fails.
    """
    m = message.lower()
    
    if any(word in m for word in ["balance", "how much"]):
        return "balance_inquiry", {}, 0.8
    
    if any(word in m for word in ["transfer", "send", "pay"]) or re.search(r'\d+\s+to\s+\w+', m):
        # Try to extract amount and recipient
        amount_match = re.search(r'(\d+)', m)
        recipient_match = re.search(r'to\s+(\w+)', m)
        
        entities = {
            "amount": float(amount_match.group(1)) if amount_match else None,
            "recipient": recipient_match.group(1) if recipient_match else None,
            "account": "123"
        }
        return "money_transfer", entities, 0.7
    
    if any(word in m for word in ["statement", "transaction", "history"]):
        return "account_statement", {}, 0.8
    
    if any(word in m for word in ["loan", "borrow", "credit"]):
        return "loan_inquiry", {}, 0.8
    
    return "fallback", {}, 0.3


def classify_intent(message: str) -> str:
    """
    Backward-compatible function for existing code.
    Returns just the intent string (for compatibility).
    """
    intent, _, _ = classify_intent_with_llm(message)
    return intent
