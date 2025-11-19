"""
FastAPI server exposing POST /chat. Uses the agent to generate an API call
description and executes the call against the backend, returning structured
responses and keeping in-memory chat history.
Supports Human-in-the-Loop approvals for high-value transactions.
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests
from typing import Optional

from agent import build_api_call
from chat_history import add_message, get_history
from persistence import persistence

app = FastAPI()


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    user_id: Optional[str] = "default_user"


class ApprovalRequest(BaseModel):
    approval_id: str
    approved: bool
    approver_id: Optional[str] = "admin"
    rejection_reason: Optional[str] = None


@app.post("/chat")
def chat(req: ChatRequest):
    add_message("user", req.message)
    
    # Build state with session tracking
    state = {"message": req.message, "user_id": req.user_id}
    if req.session_id:
        state["session_id"] = req.session_id
    
    api_call = build_api_call(req.message)

    # Handle pending approval status
    if api_call.get("status") == "pending_approval":
        reply = {
            "status": "pending_approval",
            "message": api_call.get("message"),
            "approval_id": api_call.get("approval_id"),
            "session_id": api_call.get("session_id"),
            "amount": api_call.get("amount"),
            "recipient": api_call.get("recipient")
        }
        add_message("assistant", str(reply))
        return {"reply": reply, "history": get_history()}

    if api_call.get("intent") == "fallback":
        reply = api_call.get("message", "Sorry, I don't understand.")
        add_message("assistant", reply)
        return {"reply": reply, "history": get_history()}

    if "error" in api_call:
        reply = api_call["error"]
        add_message("assistant", reply)
        return {"reply": reply, "history": get_history()}

    try:
        method = api_call.get("method", "GET").upper()
        url = api_call.get("url")
        if method == "GET":
            r = requests.get(url, params=api_call.get("params"), timeout=5)
        else:
            r = requests.post(url, json=api_call.get("json"), timeout=5)

        try:
            data = r.json()
        except Exception:
            data = {"text": r.text}

        reply = {"intent": api_call.get("intent"), "status_code": r.status_code, "data": data}
        add_message("assistant", str(reply))
        return {"reply": reply, "history": get_history()}

    except requests.RequestException as e:
        reply = f"Error calling backend: {e}"
        add_message("assistant", reply)
        return {"reply": reply, "history": get_history()}


@app.post("/approve")
def approve_transfer(req: ApprovalRequest):
    """Approve or reject a pending transfer."""
    if req.approved:
        result = persistence.approve_request(req.approval_id, req.approver_id)
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        
        # Resume workflow with approved state
        session_id = result["session_id"]
        request_data = result["request_data"]
        
        # Execute the approved transfer
        try:
            r = requests.post(
                "http://localhost:8081/api/transfer",
                json=request_data,
                timeout=5
            )
            transfer_result = r.json() if r.ok else {"error": r.text}
            
            return {
                "status": "approved",
                "approval_id": req.approval_id,
                "session_id": session_id,
                "transfer_result": transfer_result
            }
        except requests.RequestException as e:
            return {
                "status": "approved",
                "approval_id": req.approval_id,
                "error": f"Transfer execution failed: {e}"
            }
    else:
        result = persistence.reject_request(
            req.approval_id,
            req.rejection_reason or "Rejected by approver",
            req.approver_id
        )
        return {
            "status": "rejected",
            "approval_id": req.approval_id,
            "reason": req.rejection_reason
        }


@app.get("/approvals/pending")
def get_pending_approvals():
    """Get all pending approval requests."""
    return {"pending_approvals": persistence.get_pending_approvals()}


@app.get("/session/{session_id}")
def get_session_status(session_id: str):
    """Get session status."""
    status = persistence.get_session_status(session_id)
    if not status:
        raise HTTPException(status_code=404, detail="Session not found")
    return status


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
