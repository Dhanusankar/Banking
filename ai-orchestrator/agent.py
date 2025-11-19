from intent_classifier import classify_intent
# Defer langgraph import to runtime inside `build_api_call` so the
# FastAPI server can start even if langgraph isn't installed.
try:
    # keep a module-level reference if available (optional)
    from langgraph.graph import StateGraph, END  # type: ignore
except Exception:
    StateGraph = None
    END = None
from transfer_extractor import extract_transfer_details

def balance_tool(state: dict) -> dict:
    print(f"DEBUG: balance_tool state={state}")
    message = state.get("message", "")
    return {
        "intent": "balance_inquiry",
        "method": "GET",
        "url": "http://localhost:8081/api/balance",
        "params": {"accountId": "123"},
        "message": message
    }

def transfer_tool(state: dict) -> dict:
    print(f"DEBUG: transfer_tool state={state}")
    message = state.get("message", "")
    details = extract_transfer_details(message)
    if not details:
        return {"intent": "money_transfer", "error": "Could not parse transfer details", "message": message}
    to_account = details.get("recipient", "kiran").lower()
    amount = details.get("amount")
    return {
        "intent": "money_transfer",
        "method": "POST",
        "url": "http://localhost:8081/api/transfer",
        "json": {
            "fromAccount": "123",
            "toAccount": to_account,
            "amount": amount
        },
        "message": message
    }

def fallback_tool(state: dict) -> dict:
    print(f"DEBUG: fallback_tool state={state}")
    return {"intent": "fallback", "message": "Sorry, I don't understand.", "original_message": state.get("message", "")}

def validate_input_tool(state: dict) -> dict:
    print(f"DEBUG: validate_input_tool state={state}")
    message = state.get("message", "")
    if "account" not in message.lower():
        return {"intent": "validation_failed", "error": "Account number missing.", "message": message}
    return {"intent": "validation_passed", "message": message}

def account_statement_tool(state: dict) -> dict:
    print(f"DEBUG: account_statement_tool state={state}")
    message = state.get("message", "")
    return {
        "intent": "account_statement",
        "method": "GET",
        "url": "http://localhost:8081/api/statement",
        "params": {"accountId": "123"},
        "message": message
    }

def loan_inquiry_tool(state: dict) -> dict:
    print(f"DEBUG: loan_inquiry_tool state={state}")
    message = state.get("message", "")
    return {
        "intent": "loan_inquiry",
        "method": "GET",
        "url": "http://localhost:8081/api/loan",
        "params": {"accountId": "123"},
        "message": message
    }

def build_api_call(message: str) -> dict:
    intent = classify_intent(message)

    # If langgraph is available, use the graph-based workflow.
    if StateGraph is not None:
        graph = StateGraph(dict)
        graph.add_node("validate_input", validate_input_tool)
        graph.add_node("balance_inquiry", balance_tool)
        graph.add_node("money_transfer", transfer_tool)
        graph.add_node("account_statement", account_statement_tool)
        graph.add_node("loan_inquiry", loan_inquiry_tool)
        graph.add_node("fallback", fallback_tool)
        graph.add_edge("validate_input", intent)
        graph.add_edge("balance_inquiry", END)
        graph.add_edge("money_transfer", END)
        graph.add_edge("account_statement", END)
        graph.add_edge("loan_inquiry", END)
        graph.add_edge("fallback", END)
        graph.set_entry_point("validate_input")
        compiled_graph = graph.compile()
        result = compiled_graph.invoke({"message": message})
        return result

    # Fallback: simple imperative mapping (no langgraph required)
    state = {"message": message}
    # First validate
    v = validate_input_tool(state)
    if v.get("intent") == "validation_failed":
        return v

    # Route based on classified intent
    if intent == "balance_inquiry":
        return balance_tool(state)
    if intent == "money_transfer":
        return transfer_tool(state)
    if intent == "account_statement":
        return account_statement_tool(state)
    if intent == "loan_inquiry":
        return loan_inquiry_tool(state)
    return fallback_tool(state)