"""
Production FastAPI server with workflow management endpoints.
Supports checkpointing, HIL approvals, and session-based workflow execution.
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import uuid

from banking_graph import banking_graph, resume_workflow
from session_manager import session_manager, SessionStatus
from hil_node import transfer_hil_node
from checkpoint_store import checkpoint_store
from persistence import persistence

app = FastAPI(title="Banking AI Orchestrator", version="2.0")


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    user_id: Optional[str] = "default_user"


class WorkflowApprovalRequest(BaseModel):
    approver_id: str
    approved: bool
    reason: Optional[str] = None


class WorkflowResumeRequest(BaseModel):
    action: str  # "approved" or "rejected"
    approver_id: str
    reason: Optional[str] = None


@app.post("/chat")
def chat(req: ChatRequest):
    """
    Main chat endpoint with session management and checkpointing.
    
    Workflow:
        1. Get or create session
        2. Add message to conversation history
        3. Execute workflow graph (preserving conversational context)
        4. Save checkpoints automatically
        5. Return result (may be PENDING_APPROVAL for HIL)
    """
    # Get or create session
    session = session_manager.get_or_create_session(
        session_id=req.session_id,
        user_id=req.user_id,
        workflow_type="banking"
    )
    
    # Add user message to conversation
    session.add_message("user", req.message)
    
    # Prepare initial state - preserve conversational context from previous state
    initial_state = {
        "message": req.message,
        "user_id": req.user_id,
        "session_id": session.session_id,
        "from_account": "123",  # Default account
        "execution_history": []
    }
    
    # Preserve conversational context from previous message if available
    if session.workflow_state:
        prev_state = session.workflow_state
        # Carry forward context if user is completing a partial request
        if prev_state.get("awaiting_completion"):
            initial_state["context_amount"] = prev_state.get("context_amount")
            initial_state["context_recipient"] = prev_state.get("context_recipient")
            print(f"🔗 Restoring conversational context: amount={initial_state.get('context_amount')}, recipient={initial_state.get('context_recipient')}")
    
    # Check for idempotent execution
    if session.is_idempotent_execution():
        print(f"⚠️  Idempotent execution detected for session: {session.session_id[:8]}...")
    
    session.increment_execution()
    
    try:
        # Execute workflow graph
        result = banking_graph.invoke(initial_state)
        
        # Extract response
        response = result.get("response", {})
        
        # Check if workflow is pending approval
        if response.get("status") == "PENDING_APPROVAL":
            session.set_status(SessionStatus.PENDING_APPROVAL)
            session.update_state(result, node_id="money_transfer_hil")
            session_manager.save_session(session)
            
            return {
                "reply": response,
                "session_id": session.session_id,
                "status": "PENDING_APPROVAL"
            }
        
        # Check if awaiting more info (conversational flow)
        if response.get("status") == "awaiting_info":
            session.set_status(SessionStatus.ACTIVE)
            session.update_state(result)  # Save context for next message
            session.add_message("assistant", response.get("message", ""))
            session_manager.save_session(session)
            
            return {
                "reply": response,
                "session_id": session.session_id,
                "status": "awaiting_info"
            }
        
        # Check for errors
        if result.get("error"):
            session.add_message("assistant", f"Error: {result['error']}")
            return {
                "reply": {"error": result["error"]},
                "session_id": session.session_id
            }
        
        # Success - update session and clear conversational context
        session.set_status(SessionStatus.COMPLETED)
        session.update_state(result)
        session.add_message("assistant", str(response))
        session_manager.save_session(session)
        
        return {
            "reply": response,
            "session_id": session.session_id,
            "execution_history": result.get("execution_history", [])
        }
    
    except Exception as e:
        session.set_status(SessionStatus.FAILED)
        session.add_message("assistant", f"Error: {str(e)}")
        session_manager.save_session(session)
        
        return {
            "reply": {"error": str(e)},
            "session_id": session.session_id
        }


@app.post("/workflow/{session_id}/approve")
def approve_workflow(session_id: str, req: WorkflowApprovalRequest):
    """
    Approve a pending workflow and resume execution.
    
    Workflow:
        1. Load session and checkpoint
        2. Apply approval decision via HIL node
        3. Resume workflow execution
        4. Return final result
    """
    # Validate session exists
    session = session_manager.get_session(session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if session.status != SessionStatus.PENDING_APPROVAL:
        raise HTTPException(
            status_code=400,
            detail=f"Session not pending approval (status: {session.status.value})"
        )
    
    try:
        if req.approved:
            # Approve via HIL node
            hil_result = transfer_hil_node.approve(
                session_id=session_id,
                approver_id=req.approver_id,
                reason=req.reason
            )
            
            # Resume workflow
            workflow_result = resume_workflow(session_id, "approved")
            
            # Update session
            session.set_status(SessionStatus.APPROVED)
            session.add_message(
                "system",
                f"Transfer approved by {req.approver_id}",
                metadata={"approver_id": req.approver_id}
            )
            session_manager.save_session(session)
            
            return {
                "status": "approved",
                "session_id": session_id,
                "result": workflow_result,
                "approved_by": req.approver_id
            }
        else:
            # Reject via HIL node
            hil_result = transfer_hil_node.reject(
                session_id=session_id,
                approver_id=req.approver_id,
                reason=req.reason or "Rejected by approver"
            )
            
            # Update session
            session.set_status(SessionStatus.REJECTED)
            session.add_message(
                "system",
                f"Transfer rejected by {req.approver_id}: {req.reason}",
                metadata={"approver_id": req.approver_id, "reason": req.reason}
            )
            session_manager.save_session(session)
            
            return {
                "status": "rejected",
                "session_id": session_id,
                "reason": req.reason,
                "rejected_by": req.approver_id
            }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/workflow/{session_id}/reject")
def reject_workflow(session_id: str, req: WorkflowApprovalRequest):
    """
    Reject a pending workflow.
    Convenience endpoint that calls approve_workflow with approved=False.
    """
    req.approved = False
    return approve_workflow(session_id, req)


@app.post("/workflow/{session_id}/resume")
def resume_workflow_endpoint(session_id: str, req: WorkflowResumeRequest):
    """
    Resume a workflow with a decision.
    Generic endpoint that handles both approval and rejection.
    """
    approval_req = WorkflowApprovalRequest(
        approver_id=req.approver_id,
        approved=(req.action == "approved"),
        reason=req.reason
    )
    
    return approve_workflow(session_id, approval_req)


@app.get("/workflow/{session_id}/status")
def get_workflow_status(session_id: str):
    """
    Get the current status of a workflow session.
    
    Returns:
        Session info, current status, checkpoints, conversation history
    """
    session = session_manager.get_session(session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Get checkpoints
    checkpoints = checkpoint_store.get_checkpoint_history(session_id)
    
    return {
        "session_id": session.session_id,
        "user_id": session.user_id,
        "status": session.status.value,
        "current_node": session.current_node,
        "execution_count": session.execution_count,
        "conversation_history": [msg.to_dict() for msg in session.conversation_history],
        "workflow_state": session.workflow_state,
        "checkpoints": len(checkpoints),
        "metadata": session.metadata
    }


@app.get("/workflow/{session_id}/checkpoints")
def get_workflow_checkpoints(session_id: str):
    """Get all checkpoints for a session."""
    checkpoints = checkpoint_store.get_checkpoint_history(session_id)
    
    return {
        "session_id": session_id,
        "checkpoint_count": len(checkpoints),
        "checkpoints": checkpoints
    }


@app.delete("/workflow/{session_id}")
def delete_workflow(session_id: str):
    """Delete a workflow session and all associated data."""
    session = session_manager.get_session(session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Delete session and checkpoints
    session_manager.delete_session(session_id)
    
    return {
        "status": "deleted",
        "session_id": session_id
    }


@app.get("/approvals/pending")
def get_pending_approvals():
    """
    Get all pending approval requests.
    Legacy endpoint for backward compatibility.
    """
    return {"pending_approvals": persistence.get_pending_approvals()}


@app.post("/approve")
def approve_transfer_legacy(req: WorkflowApprovalRequest):
    """
    Legacy approval endpoint for backward compatibility.
    Routes to new workflow approval system.
    """
    # Find session_id from pending approvals
    approvals = persistence.get_pending_approvals()
    
    if not approvals:
        raise HTTPException(status_code=404, detail="No pending approvals found")
    
    # Use the first pending approval (legacy behavior)
    approval = approvals[0]
    session_id = approval["session_id"]
    
    return approve_workflow(session_id, req)


@app.get("/sessions")
def list_sessions(user_id: Optional[str] = None):
    """List all active sessions, optionally filtered by user."""
    sessions = session_manager.get_active_sessions(user_id=user_id)
    
    return {
        "session_count": len(sessions),
        "sessions": [
            {
                "session_id": s.session_id,
                "user_id": s.user_id,
                "status": s.status.value,
                "workflow_type": s.workflow_type,
                "created_at": s.metadata.get("created_at"),
                "last_activity": s.metadata.get("last_activity")
            }
            for s in sessions
        ]
    }


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "Banking AI Orchestrator",
        "version": "2.0",
        "features": [
            "checkpointing",
            "human-in-the-loop",
            "session-management",
            "workflow-resume"
        ]
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
