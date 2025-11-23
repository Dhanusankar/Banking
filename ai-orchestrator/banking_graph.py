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
from llm_classifier import classify_intent_with_llm  # NEW: LLM-powered classification
from transfer_extractor import extract_transfer_details
import requests


# Define the state schema for the banking workflow
class BankingState(TypedDict, total=False):
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
    _halt: bool  # Internal flag for pausing workflow
    confidence: float  # LLM confidence score (0.0-1.0)
    needs_approval: bool  # Flag for low-confidence requests
    approval_reason: str  # Reason for requiring approval
    # Conversational context - remember partial info from previous messages
    context_amount: float  # Amount from previous message in session
    context_recipient: str  # Recipient from previous message in session
    awaiting_completion: bool  # Flag indicating we're waiting for missing info
    # Conversational context - remember partial info from previous messages
    context_amount: float  # Amount from previous message in session
    context_recipient: str  # Recipient from previous message in session
    awaiting_completion: bool  # Flag indicating we're waiting for missing info


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
    ENHANCED: Merges current message with conversational context.
    Checkpoint: Saved after intent classification.
    """
    message = state.get("message", "")
    
    if not message or len(message.strip()) == 0:
        state["error"] = "Empty message"
        state["intent"] = "fallback"
        return state
    
    # Classify intent using LLM (Llama-3)
    intent, entities, confidence = classify_intent_with_llm(message)
    state["intent"] = intent
    state["confidence"] = confidence
    
    # Extract current message entities
    current_amount = None
    current_recipient = None
    
    if entities and isinstance(entities, dict):
        if "amount" in entities and entities.get("amount") is not None:
            current_amount = float(entities["amount"])
        if "recipient" in entities and entities.get("recipient") is not None:
            current_recipient = entities["recipient"]
        if "account" in entities and entities.get("account") is not None:
            state["from_account"] = entities["account"]
    
    # Merge with conversational context from previous messages
    context_amount = state.get("context_amount")
    context_recipient = state.get("context_recipient")
    
    # Priority: current message > context from previous message
    if current_amount is not None:
        state["amount"] = current_amount
        print(f"💬 Using amount from current message: {current_amount}")
    elif context_amount is not None:
        state["amount"] = context_amount
        print(f"🔗 Carrying forward amount from context: {context_amount}")
    
    if current_recipient is not None:
        state["recipient"] = current_recipient
        print(f"💬 Using recipient from current message: {current_recipient}")
    elif context_recipient is not None:
        state["recipient"] = context_recipient
        print(f"🔗 Carrying forward recipient from context: {context_recipient}")
    
    print(f"🤖 LLM Intent: {intent} (confidence: {confidence:.2f})")
    return state


@checkpoint_wrapper("confidence_check")
def confidence_check_node(state: BankingState) -> BankingState:
    """
    Check LLM confidence score and decide if HIL approval is needed.
    If confidence < threshold, request human review.
    ENHANCED: Stores partial info in context and asks for missing details conversationally.
    Checkpoint: Saved before potential HIL routing.
    """
    confidence = state.get("confidence", 0.5)
    intent = state.get("intent", "fallback")
    threshold = 0.80  # Confidence threshold for automatic processing
    
    # Check for low confidence
    if confidence < threshold:
        print(f"⚠️ Low confidence ({confidence:.2f} < {threshold}) - Requires human approval")
        state["needs_approval"] = True
        state["approval_reason"] = f"Low LLM confidence: {confidence:.2f}"
        return state
    
    # Additional validation: Check if transfer intent has missing/vague critical info
    if intent == "money_transfer":
        amount = state.get("amount")
        recipient = state.get("recipient")
        
        # Check for missing values
        if amount is None or recipient is None:
            print(f"⚠️ Incomplete transfer request (amount={amount}, recipient={recipient}) - Requires human clarification")
            
            # Store partial info in context for next message
            if amount is not None:
                state["context_amount"] = amount
                print(f"💾 Storing amount in context: {amount}")
            if recipient is not None:
                state["context_recipient"] = recipient
                print(f"💾 Storing recipient in context: {recipient}")
            
            state["needs_approval"] = True
            state["approval_reason"] = "Missing transfer details (amount or recipient)"
            state["confidence"] = 0.60
            state["awaiting_completion"] = True  # Flag for conversational flow
            
            # Set context-aware error message HERE (before routing)
            if amount is None and recipient is None:
                message = "⚠️ Please provide more details. For example: 'Transfer 1000 to Kiran'"
            elif amount is None and recipient:
                message = f"⚠️ How much would you like to send to {recipient}?"
            elif recipient is None and amount:
                message = f"⚠️ To whom would you like to send ${amount:,.2f}?"
            else:
                message = "⚠️ Please provide complete transfer details."
            
            print(f"📝 Setting response in confidence_check: {message[:60]}...")
            state["response"] = {
                "status": "awaiting_info",
                "intent": intent,
                "message": message
            }
            return state
        
        # Check for vague/unclear recipients
        vague_recipients = ["someone", "somebody", "anyone", "person", "them", "him", "her", "user", "account"]
        if isinstance(recipient, str) and recipient.lower() in vague_recipients:
            print(f"⚠️ Unclear recipient '{recipient}' - Requires clarification")
            
            # Store amount in context if available
            if amount is not None:
                state["context_amount"] = amount
                print(f"💾 Storing amount in context: {amount}")
            
            state["needs_approval"] = True
            state["approval_reason"] = f"Unclear recipient: '{recipient}'"
            state["confidence"] = 0.65
            state["awaiting_completion"] = True
            
            # Set error message for vague recipient
            amount_val = amount if amount else 0
            state["response"] = {
                "status": "awaiting_info",
                "intent": intent,
                "message": f"⚠️ Please provide a specific recipient name. For example: 'Kiran' or 'Account 12345'"
            }
            return state
        
        # All info present and valid - check if this was completed conversationally
        # If user provided info across multiple messages, require HIL approval for safety
        context_amount = state.get("context_amount")
        context_recipient = state.get("context_recipient")
        used_context = (context_amount is not None or context_recipient is not None)
        
        if used_context:
            print(f"🔗 Transfer completed using conversational context - will require HIL approval")
            state["needs_approval"] = True
            state["approval_reason"] = "Transfer completed conversationally (requires verification)"
            state["awaiting_completion"] = False
        else:
            print(f"✓ Complete transfer request: ${amount:,.2f} to {recipient}")
            state["awaiting_completion"] = False
            state["needs_approval"] = False
    else:
        # Non-transfer intents - just check confidence
        print(f"✓ High confidence ({confidence:.2f}) - Proceeding automatically")
        state["needs_approval"] = False
    
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
    Prepare money transfer - use already-extracted entities from state.
    For conversational flows, entities are already merged in validate_input_node.
    Checkpoint: Saved before HIL check.
    """
    # Get entities from state (already extracted and merged with context)
    amount = state.get("amount")
    recipient = state.get("recipient")
    from_account = state.get("from_account", "123")
    
    # Validate we have required info
    if amount is None or recipient is None:
        state["error"] = f"Missing transfer details: amount={amount}, recipient={recipient}"
        print(f"❌ Transfer prepare failed: amount={amount}, recipient={recipient}")
        return state
    
    # Prepare request data for backend
    state["request_data"] = {
        "fromAccount": from_account,
        "toAccount": recipient,
        "amount": amount
    }
    
    # Check if we should auto-approve (low value, non-conversational)
    needs_approval = state.get("needs_approval", False)
    approval_reason = state.get("approval_reason", "")
    
    # Auto-approve low-value non-conversational transfers
    if amount < 5000 and not (needs_approval and "conversationally" in approval_reason):
        state["hil_decision"] = {"approved": True, "auto": True, "reason": "Low value transfer"}
        print(f"✅ Auto-approved low-value transfer: ${amount:,.2f} → {recipient}")
    
    print(f"💰 Transfer prepared: ${amount:,.2f} → {recipient}")
    return state


def money_transfer_hil_node(state: BankingState) -> BankingState:
    """
    Human-in-the-Loop approval node for high-value transfers.
    Shows complete transfer details including info from conversational context.
    Checkpoint: Automatically saved by HIL node when approval is needed.
    """
    session_id = state.get("session_id")
    user_id = state.get("user_id", "default_user")
    amount = state.get("amount", 0)
    recipient = state.get("recipient", "Unknown")
    
    # Update the approval message to show complete transfer details
    approval_message = f"💰 Transfer Approval Required:\n\n"
    approval_message += f"Amount: ${amount:,.2f}\n"
    approval_message += f"Recipient: {recipient}\n"
    approval_message += f"From Account: {state.get('from_account', '123')}\n\n"
    approval_message += "Please review and approve this transaction."
    
    print(f"⏸️  Requesting approval for: ${amount:,.2f} → {recipient}")
    
    # Execute HIL check
    hil_result = transfer_hil_node.execute(state, session_id, user_id)
    
    if hil_result["status"] == "PENDING_APPROVAL":
        # Enhance the HIL result with complete transfer details
        hil_result["transfer_details"] = {
            "amount": amount,
            "recipient": recipient,
            "from_account": state.get("from_account", "123")
        }
        hil_result["message"] = approval_message
        
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
        print(f"✓ Transfer auto-approved: ${amount:,.2f} → {recipient} (below threshold)")
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
    
    # If request_data is empty (e.g., after resume), rebuild it from state
    if not request_data or not request_data.get("amount"):
        amount = state.get("amount")
        recipient = state.get("recipient")
        from_account = state.get("from_account", "123")
        
        if amount is None or recipient is None:
            state["error"] = f"Cannot execute transfer: missing amount={amount}, recipient={recipient}"
            print(f"❌ {state['error']}")
            return state
        
        request_data = {
            "fromAccount": from_account,
            "toAccount": recipient,
            "amount": amount
        }
        state["request_data"] = request_data
        print(f"🔧 Rebuilt request_data from state: {request_data}")
    
    print(f"🔄 Executing transfer API call to {BACKEND_URL}/api/transfer")
    print(f"📦 Request data: {request_data}")
    
    try:
        url = f"{BACKEND_URL}/api/transfer"
        response = requests.post(url, json=request_data, timeout=5)
        
        print(f"📡 Backend response status: {response.status_code}")
        print(f"📡 Backend response body: {response.text}")
        
        if response.ok:
            data = response.json()
            state["response"] = {
                "intent": "money_transfer",
                "status": "success",
                "data": data,
                "approved_by": hil_decision.get("approver_id", "auto")
            }
            print(f"✓ Transfer executed successfully: ${request_data['amount']} → {request_data['toAccount']}")
            
            # Clear conversational context after successful transfer
            state["context_amount"] = None
            state["context_recipient"] = None
            state["awaiting_completion"] = False
            print("🧹 Cleared conversational context after successful transfer")
        else:
            state["error"] = f"Transfer failed: {response.status_code} - {response.text}"
            print(f"❌ Transfer failed: {response.status_code}")
    
    except Exception as e:
        state["error"] = f"Transfer execution failed: {str(e)}"
        print(f"❌ Transfer execution exception: {str(e)}")
    
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
    Handle unrecognized intents or incomplete requests.
    Checkpoint: Saved for error tracking.
    """
    # If response was already set (e.g., missing transfer details), keep it
    existing_response = state.get("response")
    
    print(f"🔍 Fallback node received response: {existing_response}")
    
    if existing_response and isinstance(existing_response, dict) and existing_response.get("message"):
        # Keep the existing custom response
        print(f"✓ Keeping custom response: {existing_response.get('message', '')[:50]}...")
        return state
    
    # Set default fallback message
    print("⚠️ No custom response found, using default fallback")
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
    """
    Route to HIL node or directly to execution.
    HIL triggered if:
    1. Amount >= $5000 OR
    2. Transfer was completed conversationally (safety check)
    """
    if state.get("error"):
        return END
    
    amount = state.get("amount", 0)
    needs_approval = state.get("needs_approval", False)
    approval_reason = state.get("approval_reason", "")
    
    # Always require HIL for conversational transfers (extra verification)
    if needs_approval and "conversationally" in approval_reason:
        print(f"🔀 Routing to HIL - conversational transfer: ${amount:,.2f}")
        return "money_transfer_hil"
    
    # Require HIL for high-value transfers (>= $5000)
    if amount >= 5000:
        print(f"🔀 Routing to HIL - high value: ${amount:,.2f}")
        return "money_transfer_hil"
    
    # Low-value, non-conversational transfers go directly to execution
    # (hil_decision already set in money_transfer_prepare_node)
    print(f"🔀 Bypassing HIL - executing low value transfer: ${amount:,.2f}")
    return "money_transfer_execute"


def route_after_hil(state: BankingState) -> str:
    """
    Route after HIL check - halt if pending, execute if approved.
    For low-confidence requests, route back to intent-specific node.
    For transfers, execute the transfer.
    """
    if state.get("_halt"):
        return END
    
    # Check if this was a low-confidence request (not a transfer)
    needs_approval = state.get("needs_approval", False)
    intent = state.get("intent", "fallback")
    
    if needs_approval and intent != "money_transfer":
        # Low confidence request approved - route to appropriate handler
        routing_map = {
            "balance_inquiry": "balance_inquiry",
            "account_statement": "account_statement",
            "loan_inquiry": "loan_inquiry",
            "fallback": "fallback"
        }
        return routing_map.get(intent, "fallback")
    
    # Transfer requests always go to execution
    return "money_transfer_execute"


def route_after_confidence_check(state: BankingState) -> str:
    """
    Route based on confidence score and intent.
    Low confidence → HIL approval required OR fallback for missing info
    Conversational transfers → Always to HIL for verification
    High confidence → Route to intent-specific node
    """
    needs_approval = state.get("needs_approval", False)
    intent = state.get("intent", "fallback")
    approval_reason = state.get("approval_reason", "")
    
    # If needs approval due to missing/unclear details, route to fallback
    # (response already set in confidence_check_node)
    if needs_approval and ("Missing transfer details" in approval_reason or "Unclear recipient" in approval_reason):
        print("🔀 Routing to fallback - missing critical transfer information")
        return "fallback"
    
    # If conversational transfer (completed across multiple messages), go to HIL
    if needs_approval and "conversationally" in approval_reason:
        print("🔀 Routing to HIL - conversational transfer requires verification")
        return "money_transfer_prepare"  # Will go to HIL after prepare
    
    # If low confidence, check if it's a transfer intent
    if needs_approval and "Low LLM confidence" in approval_reason:
        if intent == "money_transfer":
            print("🔀 Routing to HIL due to low confidence transfer")
            return "money_transfer_hil"
        else:
            print("🔀 Routing to fallback due to low confidence")
            return "fallback"
    
    # Other approval reasons (shouldn't reach here normally)
    if needs_approval:
        print("🔀 Routing to fallback due to approval needed")
        return "fallback"
    
    # Otherwise route by intent
    routing_map = {
        "balance_inquiry": "balance_inquiry",
        "money_transfer": "money_transfer_prepare",
        "account_statement": "account_statement",
        "loan_inquiry": "loan_inquiry",
        "fallback": "fallback"
    }
    
    route = routing_map.get(intent, "fallback")
    print(f"🔀 High confidence - routing to: {route}")
    return route


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
    workflow.add_node("confidence_check", confidence_check_node)  # NEW: Confidence-based routing
    workflow.add_node("balance_inquiry", balance_inquiry_node)
    workflow.add_node("money_transfer_prepare", money_transfer_prepare_node)
    workflow.add_node("money_transfer_hil", money_transfer_hil_node)
    workflow.add_node("money_transfer_execute", money_transfer_execute_node)
    workflow.add_node("account_statement", account_statement_node)
    workflow.add_node("loan_inquiry", loan_inquiry_node)
    workflow.add_node("fallback", fallback_node)
    
    # Set entry point
    workflow.set_entry_point("validate_input")
    
    # Add confidence check after validation (NEW ROUTING)
    workflow.add_edge("validate_input", "confidence_check")
    
    # Add conditional routing after confidence check
    workflow.add_conditional_edges(
        "confidence_check",
        route_after_confidence_check,
        {
            "balance_inquiry": "balance_inquiry",
            "money_transfer_prepare": "money_transfer_prepare",
            "account_statement": "account_statement",
            "loan_inquiry": "loan_inquiry",
            "fallback": "fallback",
            "money_transfer_hil": "money_transfer_hil"  # Direct to HIL for low confidence
        }
    )
    
    # Transfer workflow routing
    workflow.add_conditional_edges(
        "money_transfer_prepare",
        route_after_transfer_prepare,
        {
            "money_transfer_hil": "money_transfer_hil",
            "money_transfer_execute": "money_transfer_execute",  # Direct execution for low-value
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
    
    # Extract workflow_state if checkpoint contains Session object
    if "workflow_state" in state:
        print(f"🔧 Extracting workflow_state from Session object")
        state = state["workflow_state"]
    
    # DEBUG: Print state contents
    print(f"🔍 DEBUG - Loaded state keys: {list(state.keys())}")
    print(f"🔍 DEBUG - request_data in state: {state.get('request_data')}")
    print(f"🔍 DEBUG - amount in state: {state.get('amount')}")
    print(f"🔍 DEBUG - recipient in state: {state.get('recipient')}")
    
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

print("[OK] Banking workflow graph built with checkpointing and HIL")
