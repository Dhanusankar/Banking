"""
Production-grade LangGraph workflow for banking operations.
Includes automatic checkpointing, HIL nodes, and resume capabilities.
"""
from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, END
import operator
import os

from checkpoint_store import checkpoint_store
from hil_node import transfer_hil_node
from session_manager import session_manager, SessionStatus
from intent_classifier import classify_intent
from transfer_extractor import extract_transfer_details
import requests


# Define the state schema for the banking workflow
class BankingState(TypedDict):
    """State schema for banking workflow with full context."""
    message: str
    intent: str
    user_id: str
    session_id: str
    amount: float
    recipient: str
    from_account: str
    request_data: dict
    response: dict
    error: str
    hil_decision: dict
    execution_history: Annotated[list, operator.add]


# Backend API configuration (supports cloud deployment)
BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8081")
# Add https:// scheme if not present (for Render hostport property)
if BACKEND_URL and not BACKEND_URL.startswith(("http://", "https://")):
    BACKEND_URL = f"https://{BACKEND_URL}"


def checkpoint_wrapper(node_id: str):
    """
    Decorator to automatically checkpoint node execution.
    
    Usage:
        @checkpoint_wrapper("validate_input")
        def validate_input_node(state: BankingState) -> BankingState:
            ...
    """
    def decorator(func):
        def wrapper(state: BankingState) -> BankingState:
            session_id = state.get("session_id")
            
            # Save checkpoint before execution
            if session_id:
                checkpoint_store.save_checkpoint(
                    session_id=session_id,
                    node_id=f"{node_id}_start",
                    state=state,
                    metadata={"node": node_id, "phase": "start"}
                )
            
            # Execute node
            result = func(state)
            
            # Add to execution history
            if "execution_history" not in result:
                result["execution_history"] = []
            result["execution_history"].append({
                "node_id": node_id,
                "timestamp": checkpoint_store.backend.__class__.__name__
            })
            
            # Save checkpoint after execution
            if session_id:
                checkpoint_store.save_checkpoint(
                    session_id=session_id,
                    node_id=f"{node_id}_end",
                    state=result,
                    metadata={"node": node_id, "phase": "end"}
                )
            
            return result
        
        return wrapper
    return decorator


@checkpoint_wrapper("validate_input")
def validate_input_node(state: BankingState) -> BankingState:
    """
    Validate user input and classify intent.
    Checkpoint: Saved after intent classification.
    """
    message = state.get("message", "")
    
    if not message or len(message.strip()) == 0:
        state["error"] = "Empty message"
        state["intent"] = "fallback"
        return state
    
    # Classify intent
    intent = classify_intent(message)
    state["intent"] = intent
    
    print(f"📋 Intent classified: {intent}")
    return state


@checkpoint_wrapper("balance_inquiry")
def balance_inquiry_node(state: BankingState) -> BankingState:
    """
    Handle balance inquiry requests.
    Checkpoint: Saved after API call.
    """
    account_id = state.get("from_account", "123")
    
    try:
        url = f"{BACKEND_URL}/api/balance"
        response = requests.get(url, params={"accountId": account_id}, timeout=5)
        
        if response.ok:
            data = response.json()
            state["response"] = {
                "intent": "balance_inquiry",
                "status": "success",
                "data": data
            }
        else:
            state["error"] = f"Backend error: {response.status_code}"
    
    except Exception as e:
        state["error"] = f"API call failed: {str(e)}"
    
    return state


@checkpoint_wrapper("money_transfer_prepare")
def money_transfer_prepare_node(state: BankingState) -> BankingState:
    """
    Prepare money transfer - extract details and validate.
    Checkpoint: Saved before HIL check.
    """
    message = state.get("message", "")
    
    # Extract transfer details
    details = extract_transfer_details(message)
    
    if "error" in details:
        state["error"] = details["error"]
        return state
    
    state["amount"] = details["amount"]
    state["recipient"] = details["recipient"]
    state["from_account"] = details.get("from_account", "123")
    
    # Prepare request data for backend
    state["request_data"] = {
        "fromAccount": state["from_account"],
        "toAccount": state["recipient"],
        "amount": state["amount"]
    }
    
    print(f"💰 Transfer prepared: ${state['amount']} → {state['recipient']}")
    return state


def money_transfer_hil_node(state: BankingState) -> BankingState:
    """
    Human-in-the-Loop approval node for high-value transfers.
    Checkpoint: Automatically saved by HIL node when approval is needed.
    """
    session_id = state.get("session_id")
    user_id = state.get("user_id", "default_user")
    amount = state.get("amount", 0)
    
    # Execute HIL check
    hil_result = transfer_hil_node.execute(state, session_id, user_id)
    
    if hil_result["status"] == "PENDING_APPROVAL":
        # Workflow pauses here - state is saved in checkpoint
        print(f"⏸️  Transfer paused for approval: ${amount}")
        
        # Update session status
        session = session_manager.get_session(session_id)
        if session:
            session.set_status(SessionStatus.PENDING_APPROVAL)
            session_manager.save_session(session)
        
        # Return special status to halt workflow
        state["response"] = hil_result
        state["_halt"] = True  # Signal to stop execution
        return state
    
    elif hil_result["status"] == "BYPASSED":
        # Low value transfer - continue automatically
        print(f"✓ Transfer auto-approved: ${amount} (below threshold)")
        state["hil_decision"] = {"approved": True, "auto": True}
    
    return state


@checkpoint_wrapper("money_transfer_execute")
def money_transfer_execute_node(state: BankingState) -> BankingState:
    """
    Execute the approved money transfer.
    Checkpoint: Saved after transfer completion.
    """
    # Check if we have an HIL decision
    hil_decision = state.get("hil_decision", {})
    
    if not hil_decision.get("approved"):
        state["error"] = "Transfer not approved"
        return state
    
    request_data = state.get("request_data", {})
    
    try:
        url = f"{BACKEND_URL}/api/transfer"
        response = requests.post(url, json=request_data, timeout=5)
        
        if response.ok:
            data = response.json()
            state["response"] = {
                "intent": "money_transfer",
                "status": "success",
                "data": data,
                "approved_by": hil_decision.get("approver_id", "auto")
            }
            print(f"✓ Transfer executed: ${request_data['amount']} → {request_data['toAccount']}")
        else:
            state["error"] = f"Transfer failed: {response.status_code}"
    
    except Exception as e:
        state["error"] = f"Transfer execution failed: {str(e)}"
    
    return state


@checkpoint_wrapper("account_statement")
def account_statement_node(state: BankingState) -> BankingState:
    """
    Retrieve account statement.
    Checkpoint: Saved after API call.
    """
    account_id = state.get("from_account", "123")
    
    try:
        url = f"{BACKEND_URL}/api/statement"
        response = requests.get(url, params={"accountId": account_id}, timeout=5)
        
        if response.ok:
            # Backend returns text for POC
            state["response"] = {
                "intent": "account_statement",
                "status": "success",
                "data": {"statement": response.text}
            }
        else:
            state["error"] = f"Backend error: {response.status_code}"
    
    except Exception as e:
        state["error"] = f"API call failed: {str(e)}"
    
    return state


@checkpoint_wrapper("loan_inquiry")
def loan_inquiry_node(state: BankingState) -> BankingState:
    """
    Handle loan inquiry requests.
    Checkpoint: Saved after API call.
    """
    account_id = state.get("from_account", "123")
    
    try:
        url = f"{BACKEND_URL}/api/loan"
        response = requests.get(url, params={"accountId": account_id}, timeout=5)
        
        if response.ok:
            state["response"] = {
                "intent": "loan_inquiry",
                "status": "success",
                "data": {"loan_info": response.text}
            }
        else:
            state["error"] = f"Backend error: {response.status_code}"
    
    except Exception as e:
        state["error"] = f"API call failed: {str(e)}"
    
    return state


@checkpoint_wrapper("fallback")
def fallback_node(state: BankingState) -> BankingState:
    """
    Handle unrecognized intents.
    Checkpoint: Saved for error tracking.
    """
    state["response"] = {
        "intent": "fallback",
        "message": "I didn't understand that. Try: 'What's my balance?' or 'Transfer 1000 to Kiran'"
    }
    return state


def route_by_intent(state: BankingState) -> str:
    """Route to appropriate node based on intent."""
    intent = state.get("intent", "fallback")
    
    routing_map = {
        "balance_inquiry": "balance_inquiry",
        "money_transfer": "money_transfer_prepare",
        "account_statement": "account_statement",
        "loan_inquiry": "loan_inquiry",
        "fallback": "fallback"
    }
    
    return routing_map.get(intent, "fallback")


def route_after_transfer_prepare(state: BankingState) -> str:
    """Route to HIL node or directly to execution."""
    if state.get("error"):
        return END
    
    return "money_transfer_hil"


def route_after_hil(state: BankingState) -> str:
    """Route after HIL check - halt if pending, execute if approved."""
    if state.get("_halt"):
        return END
    
    return "money_transfer_execute"


def build_banking_graph() -> StateGraph:
    """
    Build the complete banking workflow graph with checkpointing and HIL.
    
    Graph structure:
        Entry → Validate → Route by Intent
                              ├─→ Balance Inquiry → End
                              ├─→ Transfer Prepare → HIL Check → Execute → End
                              ├─→ Account Statement → End
                              ├─→ Loan Inquiry → End
                              └─→ Fallback → End
    
    Checkpoints are saved:
        1. After intent classification (validate_input)
        2. After transfer preparation (money_transfer_prepare)
        3. Before HIL approval (money_transfer_hil)
        4. After transfer execution (money_transfer_execute)
        5. At all other node completions
    """
    workflow = StateGraph(BankingState)
    
    # Add nodes
    workflow.add_node("validate_input", validate_input_node)
    workflow.add_node("balance_inquiry", balance_inquiry_node)
    workflow.add_node("money_transfer_prepare", money_transfer_prepare_node)
    workflow.add_node("money_transfer_hil", money_transfer_hil_node)
    workflow.add_node("money_transfer_execute", money_transfer_execute_node)
    workflow.add_node("account_statement", account_statement_node)
    workflow.add_node("loan_inquiry", loan_inquiry_node)
    workflow.add_node("fallback", fallback_node)
    
    # Set entry point
    workflow.set_entry_point("validate_input")
    
    # Add conditional routing after validation
    workflow.add_conditional_edges(
        "validate_input",
        route_by_intent,
        {
            "balance_inquiry": "balance_inquiry",
            "money_transfer_prepare": "money_transfer_prepare",
            "account_statement": "account_statement",
            "loan_inquiry": "loan_inquiry",
            "fallback": "fallback"
        }
    )
    
    # Transfer workflow routing
    workflow.add_conditional_edges(
        "money_transfer_prepare",
        route_after_transfer_prepare,
        {
            "money_transfer_hil": "money_transfer_hil",
            END: END
        }
    )
    
    workflow.add_conditional_edges(
        "money_transfer_hil",
        route_after_hil,
        {
            "money_transfer_execute": "money_transfer_execute",
            END: END
        }
    )
    
    # Terminal nodes
    workflow.add_edge("balance_inquiry", END)
    workflow.add_edge("money_transfer_execute", END)
    workflow.add_edge("account_statement", END)
    workflow.add_edge("loan_inquiry", END)
    workflow.add_edge("fallback", END)
    
    return workflow.compile()


def resume_workflow(session_id: str, user_action: str = "approved") -> dict:
    """
    Resume a paused workflow from checkpoint.
    
    Args:
        session_id: Session to resume
        user_action: "approved" or "rejected"
    
    Returns:
        Workflow execution result
    """
    print(f"🔄 Resuming workflow: {session_id[:8]}... (action: {user_action})")
    
    # Load checkpoint
    checkpoint = checkpoint_store.load_checkpoint(session_id)
    
    if not checkpoint:
        return {"error": "No checkpoint found for session"}
    
    state = checkpoint["state"]
    
    # Apply approval decision
    if user_action == "approved":
        hil_result = transfer_hil_node.approve(session_id, "manager@bank.com")
        state["hil_decision"] = hil_result.get("state", {}).get("hil_decision", {})
    else:
        hil_result = transfer_hil_node.reject(session_id, "manager@bank.com", "Rejected by manager")
        return {
            "status": "rejected",
            "message": "Transfer rejected",
            "session_id": session_id
        }
    
    # Continue execution from money_transfer_execute node
    result = money_transfer_execute_node(state)
    
    # Update session
    session = session_manager.get_session(session_id)
    if session:
        session.set_status(SessionStatus.COMPLETED)
        session.update_state(result)
        session_manager.save_session(session)
    
    return result.get("response", {})


# Build the graph at module load
banking_graph = build_banking_graph()

print("✓ Banking workflow graph built with checkpointing and HIL")
