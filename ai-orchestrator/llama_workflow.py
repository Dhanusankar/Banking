"""
Complete LangGraph workflow using Llama-3 via Ollama (Local LLM)
Production-ready implementation with HIL approval for low-confidence requests

Requirements:
- Ollama running with llama3 model: ollama pull llama3
- Python 3.11+
- Dependencies: langgraph, requests

Run Ollama: ollama serve
Test model: curl http://localhost:11434/api/generate -d '{"model":"llama3","prompt":"Hello"}'
"""

from typing import TypedDict, Annotated, Literal
from langgraph.graph import StateGraph, END
import operator
import requests
import json
import re
from datetime import datetime


# ============================================================================
# STATE DEFINITION
# ============================================================================

class WorkflowState(TypedDict, total=False):
    """State schema for the LangGraph workflow."""
    user_input: str              # Original user request
    intent: str                  # Classified intent (valid/invalid)
    summary: str                 # LLM-generated summary
    entities: dict               # Extracted entities
    confidence: float            # LLM confidence score (0-1)
    needs_approval: bool         # Flag for low-confidence requests
    approval_decision: str       # Human decision: approve/reject/pending
    approval_reason: str         # Optional approval reason
    result: dict                 # Processed result
    error: str                   # Error message if any
    execution_history: Annotated[list, operator.add]  # Node execution trace
    _halt: bool                  # Internal flag to pause workflow


# ============================================================================
# OLLAMA LLAMA-3 API CLIENT
# ============================================================================

OLLAMA_API_URL = "http://localhost:11434/api/generate"
LLAMA_MODEL = "llama3"


def call_llama3(prompt: str, max_retries: int = 3) -> dict:
    """
    Call Llama-3 via Ollama API with structured JSON response.
    
    Args:
        prompt: The prompt to send to Llama-3
        max_retries: Number of retry attempts
        
    Returns:
        dict: Parsed JSON response with summary, entities, confidence
    """
    for attempt in range(max_retries):
        try:
            response = requests.post(
                OLLAMA_API_URL,
                json={
                    "model": LLAMA_MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json"  # Force JSON output
                },
                timeout=30
            )
            response.raise_for_status()
            
            # Parse Ollama response
            ollama_data = response.json()
            llm_response = ollama_data.get("response", "")
            
            # Extract JSON from response (handle markdown code blocks)
            json_match = re.search(r'\{.*\}', llm_response, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group(0))
                return result
            
            # If no JSON found, try parsing entire response
            return json.loads(llm_response)
            
        except requests.exceptions.RequestException as e:
            print(f"⚠️ Ollama API error (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt == max_retries - 1:
                return {
                    "summary": f"Error calling Llama-3: {e}",
                    "entities": {},
                    "confidence": 0.0
                }
        except json.JSONDecodeError as e:
            print(f"⚠️ JSON parse error (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt == max_retries - 1:
                return {
                    "summary": "Unable to parse LLM response",
                    "entities": {},
                    "confidence": 0.0
                }
    
    return {
        "summary": "Max retries exceeded",
        "entities": {},
        "confidence": 0.0
    }


# ============================================================================
# CHECKPOINT DECORATOR
# ============================================================================

def checkpoint_wrapper(node_id: str):
    """
    Decorator to automatically checkpoint node execution.
    Records node execution in the state's execution_history.
    """
    def decorator(func):
        def wrapper(state: WorkflowState) -> WorkflowState:
            print(f"🔄 Executing node: {node_id}")
            
            # Add to execution history
            if "execution_history" not in state:
                state["execution_history"] = []
            
            state["execution_history"].append({
                "node_id": node_id,
                "timestamp": datetime.now().isoformat()
            })
            
            # Execute the actual node function
            result = func(state)
            
            print(f"✅ Completed node: {node_id}")
            return result
        
        return wrapper
    return decorator


# ============================================================================
# NODE 1: VALIDATE INPUT
# ============================================================================

@checkpoint_wrapper("validate_input_node")
def validate_input_node(state: WorkflowState) -> WorkflowState:
    """
    Validate user input.
    If empty or invalid → set intent='invalid' and continue.
    """
    user_input = state.get("user_input", "").strip()
    
    if not user_input or len(user_input) < 3:
        state["intent"] = "invalid"
        state["error"] = "Invalid input: Request too short or empty"
        state["confidence"] = 0.0
        print("❌ Invalid input detected")
    else:
        state["intent"] = "valid"
        state["error"] = None
        print(f"✓ Valid input: {user_input[:50]}...")
    
    return state


# ============================================================================
# NODE 2: CALL LLM (LLAMA-3)
# ============================================================================

@checkpoint_wrapper("call_llm_node")
def call_llm_node(state: WorkflowState) -> WorkflowState:
    """
    Send structured prompt to Llama-3 via Ollama.
    Extract: summary, entities, confidence score.
    """
    # Skip if input is invalid
    if state.get("intent") == "invalid":
        state["summary"] = "Invalid input"
        state["entities"] = {}
        state["confidence"] = 0.0
        return state
    
    user_input = state.get("user_input", "")
    
    # Construct structured prompt for Llama-3
    prompt = f"""You are a banking AI assistant analyzing user requests.

User Request: "{user_input}"

Analyze this request and respond ONLY with valid JSON in this exact format:
{{
    "summary": "A brief 1-sentence summary of what the user wants",
    "entities": {{
        "intent": "one of: transfer, balance, statement, loan, other",
        "amount": null or number,
        "recipient": null or string,
        "account": null or string
    }},
    "confidence": 0.95
}}

Rules:
1. confidence must be between 0.0 and 1.0
2. High confidence (>0.8) for clear, specific requests
3. Low confidence (<0.8) for vague or ambiguous requests
4. Return ONLY the JSON, no explanation

JSON Response:"""

    print("🤖 Calling Llama-3 via Ollama...")
    llm_result = call_llama3(prompt)
    
    # Update state with LLM response
    state["summary"] = llm_result.get("summary", "No summary available")
    state["entities"] = llm_result.get("entities", {})
    state["confidence"] = float(llm_result.get("confidence", 0.5))
    
    print(f"📊 LLM Response:")
    print(f"   Summary: {state['summary']}")
    print(f"   Confidence: {state['confidence']:.2f}")
    print(f"   Entities: {state['entities']}")
    
    return state


# ============================================================================
# NODE 3: CONFIDENCE CHECK
# ============================================================================

@checkpoint_wrapper("confidence_check_node")
def confidence_check_node(state: WorkflowState) -> WorkflowState:
    """
    Check confidence score.
    If confidence < 0.80 → set needs_approval=True and halt workflow.
    """
    confidence = state.get("confidence", 0.0)
    threshold = 0.80
    
    if confidence < threshold:
        state["needs_approval"] = True
        state["approval_decision"] = "pending"
        state["_halt"] = True  # Pause workflow for human review
        print(f"⏸️ Low confidence ({confidence:.2f} < {threshold}) - Requires human approval")
    else:
        state["needs_approval"] = False
        print(f"✓ High confidence ({confidence:.2f}) - Proceeding automatically")
    
    return state


# ============================================================================
# NODE 4: HUMAN APPROVAL (HIL)
# ============================================================================

@checkpoint_wrapper("human_approval_node")
def human_approval_node(state: WorkflowState) -> WorkflowState:
    """
    Human-in-the-Loop approval node.
    
    Workflow pauses here until human makes a decision.
    Decision options: approve, reject
    """
    approval_decision = state.get("approval_decision", "pending")
    
    if approval_decision == "pending":
        # Workflow remains paused - waiting for external approval
        state["_halt"] = True
        print("⏳ Waiting for human approval...")
        return state
    
    elif approval_decision == "approve":
        print("✅ Request approved by human")
        state["_halt"] = False  # Resume workflow
        return state
    
    elif approval_decision == "reject":
        print("❌ Request rejected by human")
        state["error"] = f"Request rejected: {state.get('approval_reason', 'No reason provided')}"
        state["_halt"] = True  # Terminate workflow
        return state
    
    else:
        print(f"⚠️ Unknown approval decision: {approval_decision}")
        state["error"] = "Invalid approval decision"
        state["_halt"] = True
        return state


# ============================================================================
# NODE 5: HYT PROCESSING
# ============================================================================

@checkpoint_wrapper("hyt_processing_node")
def hyt_processing_node(state: WorkflowState) -> WorkflowState:
    """
    Process the validated and approved request.
    This is where actual business logic would execute.
    """
    # Skip if there's an error
    if state.get("error"):
        print("⚠️ Skipping processing due to error")
        return state
    
    print("🔧 Processing request...")
    
    # Extract entities
    entities = state.get("entities", {})
    intent = entities.get("intent", "other")
    
    # Simulate processing based on intent
    result = {
        "status": "success",
        "processed_at": datetime.now().isoformat(),
        "intent": intent,
        "confidence": state.get("confidence", 0.0),
        "summary": state.get("summary", "")
    }
    
    # Add intent-specific results
    if intent == "transfer":
        result["transfer_amount"] = entities.get("amount")
        result["transfer_recipient"] = entities.get("recipient")
        result["message"] = f"Transfer of ${entities.get('amount', 0)} to {entities.get('recipient', 'unknown')} processed"
    
    elif intent == "balance":
        result["balance"] = 50000.00  # Mock balance
        result["message"] = "Balance inquiry processed"
    
    elif intent == "statement":
        result["statement_type"] = "recent transactions"
        result["message"] = "Statement request processed"
    
    elif intent == "loan":
        result["loan_eligible"] = True
        result["max_amount"] = 100000.00
        result["message"] = "Loan inquiry processed"
    
    else:
        result["message"] = "General request processed"
    
    state["result"] = result
    print(f"✓ Processing complete: {result['message']}")
    
    return state


# ============================================================================
# NODE 6: FINALIZE
# ============================================================================

@checkpoint_wrapper("finalize_node")
def finalize_node(state: WorkflowState) -> WorkflowState:
    """
    Build final structured response for UI.
    Include all relevant information from the workflow.
    """
    print("🎯 Finalizing response...")
    
    # Build comprehensive final result
    final_result = {
        "status": "error" if state.get("error") else "success",
        "timestamp": datetime.now().isoformat(),
        "user_input": state.get("user_input", ""),
        "summary": state.get("summary", ""),
        "entities": state.get("entities", {}),
        "confidence": state.get("confidence", 0.0),
        "needed_approval": state.get("needs_approval", False),
        "approval_decision": state.get("approval_decision", "not_required"),
        "result": state.get("result", {}),
        "error": state.get("error"),
        "execution_trace": state.get("execution_history", [])
    }
    
    state["result"] = final_result
    
    print("✅ Workflow complete!")
    print(f"📋 Final Status: {final_result['status']}")
    
    return state


# ============================================================================
# ROUTING LOGIC
# ============================================================================

def route_after_confidence_check(state: WorkflowState) -> Literal["human_approval_node", "hyt_processing_node"]:
    """
    Route workflow based on confidence score.
    Low confidence → human approval
    High confidence → direct processing
    """
    if state.get("needs_approval"):
        return "human_approval_node"
    return "hyt_processing_node"


def route_after_validation(state: WorkflowState) -> Literal["call_llm_node", "finalize_node"]:
    """
    Route workflow after input validation.
    Invalid input → skip to finalization
    Valid input → proceed to LLM
    """
    if state.get("intent") == "invalid":
        return "finalize_node"
    return "call_llm_node"


def should_continue_after_approval(state: WorkflowState) -> Literal["hyt_processing_node", END]:
    """
    Route workflow after human approval.
    Approved → continue processing
    Rejected or error → terminate
    """
    if state.get("error"):
        return END
    if state.get("approval_decision") == "approve":
        return "hyt_processing_node"
    return END


# ============================================================================
# WORKFLOW GRAPH CONSTRUCTION
# ============================================================================

def build_workflow() -> StateGraph:
    """
    Build the complete LangGraph workflow with all nodes and edges.
    """
    # Create graph
    workflow = StateGraph(WorkflowState)
    
    # Add nodes
    workflow.add_node("validate_input_node", validate_input_node)
    workflow.add_node("call_llm_node", call_llm_node)
    workflow.add_node("confidence_check_node", confidence_check_node)
    workflow.add_node("human_approval_node", human_approval_node)
    workflow.add_node("hyt_processing_node", hyt_processing_node)
    workflow.add_node("finalize_node", finalize_node)
    
    # Set entry point
    workflow.set_entry_point("validate_input_node")
    
    # Add edges with routing logic
    workflow.add_conditional_edges(
        "validate_input_node",
        route_after_validation,
        {
            "call_llm_node": "call_llm_node",
            "finalize_node": "finalize_node"
        }
    )
    
    workflow.add_edge("call_llm_node", "confidence_check_node")
    
    workflow.add_conditional_edges(
        "confidence_check_node",
        route_after_confidence_check,
        {
            "human_approval_node": "human_approval_node",
            "hyt_processing_node": "hyt_processing_node"
        }
    )
    
    workflow.add_conditional_edges(
        "human_approval_node",
        should_continue_after_approval,
        {
            "hyt_processing_node": "hyt_processing_node",
            END: END
        }
    )
    
    workflow.add_edge("hyt_processing_node", "finalize_node")
    workflow.add_edge("finalize_node", END)
    
    return workflow


# ============================================================================
# WORKFLOW RUNNER
# ============================================================================

def run_workflow(user_input: str, approval_decision: str = None) -> dict:
    """
    Execute the complete workflow.
    
    Args:
        user_input: The user's request/query
        approval_decision: Optional pre-set approval decision (for testing)
        
    Returns:
        dict: Final workflow result
    """
    print("=" * 80)
    print("🚀 Starting LangGraph Workflow with Llama-3 (Ollama)")
    print("=" * 80)
    
    # Build workflow
    workflow = build_workflow()
    app = workflow.compile()
    
    # Initialize state
    initial_state = WorkflowState(
        user_input=user_input,
        execution_history=[]
    )
    
    # Add approval decision if provided
    if approval_decision:
        initial_state["approval_decision"] = approval_decision
    
    # Execute workflow
    try:
        final_state = app.invoke(initial_state)
        
        # Check if workflow is halted (needs approval)
        if final_state.get("_halt"):
            print("\n⏸️ Workflow paused - requires human approval")
            print(f"   Summary: {final_state.get('summary', 'N/A')}")
            print(f"   Confidence: {final_state.get('confidence', 0):.2f}")
            print("\n   To approve: call resume_workflow(state, 'approve')")
            print("   To reject: call resume_workflow(state, 'reject')")
        
        return final_state.get("result", final_state)
        
    except Exception as e:
        print(f"\n❌ Workflow error: {e}")
        return {
            "status": "error",
            "error": str(e)
        }


def resume_workflow(paused_state: dict, decision: str, reason: str = None) -> dict:
    """
    Resume a paused workflow with human decision.
    
    Args:
        paused_state: The state from the paused workflow
        decision: "approve" or "reject"
        reason: Optional reason for the decision
        
    Returns:
        dict: Final workflow result
    """
    print("\n" + "=" * 80)
    print(f"▶️ Resuming workflow with decision: {decision}")
    print("=" * 80)
    
    # Update state with approval decision
    paused_state["approval_decision"] = decision
    if reason:
        paused_state["approval_reason"] = reason
    paused_state["_halt"] = False
    
    # Rebuild and continue workflow
    workflow = build_workflow()
    app = workflow.compile()
    
    try:
        final_state = app.invoke(paused_state)
        return final_state.get("result", final_state)
    except Exception as e:
        print(f"\n❌ Resume error: {e}")
        return {
            "status": "error",
            "error": str(e)
        }


# ============================================================================
# MAIN - EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    print("""
╔═══════════════════════════════════════════════════════════════════════╗
║  LangGraph Workflow with Llama-3 via Ollama                          ║
║  Production-ready implementation with HIL approval                    ║
╚═══════════════════════════════════════════════════════════════════════╝

Prerequisites:
1. Install Ollama: https://ollama.ai
2. Pull Llama-3: ollama pull llama3
3. Start Ollama: ollama serve
4. Install dependencies: pip install langgraph requests

Testing the workflow:
""")
    
    # Example 1: High confidence request (auto-approved)
    print("\n📝 Example 1: High confidence request")
    print("-" * 80)
    result1 = run_workflow("Transfer $500 to John Smith account 12345")
    print(f"\n✅ Result: {json.dumps(result1, indent=2)}")
    
    # Example 2: Low confidence request (needs approval)
    print("\n\n📝 Example 2: Low confidence request")
    print("-" * 80)
    result2 = run_workflow("Send some money somewhere")
    
    if result2.get("needed_approval"):
        print("\n💡 Simulating approval...")
        # In production, this would be done by a human via API/UI
        final_result = resume_workflow(result2, "approve", "Approved after clarification")
        print(f"\n✅ Final Result: {json.dumps(final_result, indent=2)}")
    
    # Example 3: Invalid input
    print("\n\n📝 Example 3: Invalid input")
    print("-" * 80)
    result3 = run_workflow("")
    print(f"\n✅ Result: {json.dumps(result3, indent=2)}")
    
    print("\n" + "=" * 80)
    print("✅ All examples completed!")
    print("=" * 80)
