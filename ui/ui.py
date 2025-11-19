"""
Streamlit chat UI that sends messages to the AI Orchestrator (`/chat`) and
shows responses. Clean, minimal layout for the POC.
Run with: `streamlit run ui.py`
"""
import os
import streamlit as st
import requests

# Determine orchestrator URL from Streamlit secrets, environment, or fallback to localhost.
# When deploying to Streamlit Cloud, set the secret `ORCHESTRATOR_URL` to your backend URL
# (for example, https://my-backend.example.com). The app will prefer `st.secrets`, then
# the `ORCHESTRATOR_URL` env var, then `http://localhost:8000` for local development.
BASE_URL = None
try:
    BASE_URL = st.secrets.get("ORCHESTRATOR_URL")
except Exception:
    BASE_URL = None

if not BASE_URL:
    BASE_URL = os.environ.get("ORCHESTRATOR_URL")

if not BASE_URL:
    BASE_URL = "http://localhost:8000"

API_URL = f"{BASE_URL}/chat"
APPROVALS_URL = f"{BASE_URL}/approvals/pending"
APPROVE_URL = f"{BASE_URL}/approve"


def send_message(message: str):
    """Send message to orchestrator and return response JSON."""
    try:
        r = requests.post(API_URL, json={"message": message}, timeout=10)
        return r.json()
    except Exception as e:
        return {"reply": f"Error: {e}"}


def get_pending_approvals():
    """Fetch pending approval requests from orchestrator."""
    try:
        r = requests.get(APPROVALS_URL, timeout=5)
        if r.status_code == 200:
            data = r.json()
            # Handle both formats: direct list or wrapped in "pending_approvals"
            if isinstance(data, dict) and "pending_approvals" in data:
                return data["pending_approvals"]
            return data if isinstance(data, list) else []
        return []
    except Exception as e:
        st.error(f"Error fetching approvals: {e}")
        return []


def approve_transfer(approval_id: str, approved: bool, approver_id: str = "manager@bank.com"):
    """Approve or reject a transfer."""
    try:
        r = requests.post(
            APPROVE_URL,
            json={"approval_id": approval_id, "approved": approved, "approver_id": approver_id},
            timeout=10
        )
        return r.json()
    except Exception as e:
        return {"error": str(e)}


def main():
    st.set_page_config(page_title="Banking AI POC", layout="wide")
    
    # Initialize session state
    if "messages" not in st.session_state:
        st.session_state["messages"] = []
    
    # Check if there are any pending approvals
    approvals = get_pending_approvals()
    show_approval_panel = len(approvals) > 0 or st.session_state.get("pending_approval_triggered", False)
    
    # Create dynamic columns based on whether approvals exist
    if show_approval_panel:
        col1, col2 = st.columns([2, 1])
    else:
        col1 = st.container()
    
    with col1:
        st.title("💬 Banking AI — Chat")

        with st.form(key="msg_form", clear_on_submit=True):
            user_input = st.text_input("You", placeholder="Ask: What's my balance? Or Transfer 2000 to Kiran.")
            submitted = st.form_submit_button("Send")

        if submitted and user_input:
            st.session_state["messages"].append({"role": "user", "text": user_input})
            response = send_message(user_input)
            reply = response.get("reply")
            st.session_state["messages"].append({"role": "assistant", "text": str(reply)})
            
            # Check if response indicates pending approval
            if isinstance(reply, dict) and reply.get("status") == "pending_approval":
                st.session_state["pending_approval_triggered"] = True
            
            st.rerun()

        # Display messages
        for msg in st.session_state["messages"]:
            if msg["role"] == "user":
                st.write(f"**You:** {msg['text']}")
            else:
                st.info(f"🤖 Assistant: {msg['text']}")
    
    # Only show approval panel if there are pending approvals
    if show_approval_panel:
        with col2:
            st.title("⚠️ Pending Approvals")
            
            # Auto-refresh when approval is triggered
            if st.session_state.get("pending_approval_triggered"):
                st.info("🔔 New approval request detected!")
            
            if st.button("🔄 Refresh Approvals"):
                st.session_state.pop("pending_approval_triggered", None)
                st.rerun()
            
            if not approvals:
                if st.session_state.get("pending_approval_triggered"):
                    st.warning("⏳ Loading approvals...")
                    st.session_state.pop("pending_approval_triggered", None)
            else:
                st.warning(f"📋 {len(approvals)} transfer(s) awaiting approval")
                st.session_state.pop("pending_approval_triggered", None)
                
                for approval in approvals:
                    with st.expander(f"💰 ${approval['amount']:,.2f} → {approval['recipient']}"):
                        st.write(f"**Amount:** ${approval['amount']:,.2f}")
                        st.write(f"**To:** {approval['recipient']}")
                        st.write(f"**Requested:** {approval['requested_at']}")
                        st.write(f"**Approval ID:** `{approval['approval_id']}`")
                        
                        # Show request details if available
                        if 'request_data' in approval:
                            request = approval['request_data']
                            if 'fromAccount' in request:
                                st.write(f"**From Account:** {request['fromAccount']}")
                        
                        col_approve, col_reject = st.columns(2)
                        
                        with col_approve:
                            if st.button("✅ Approve", key=f"approve_{approval['approval_id']}"):
                                result = approve_transfer(approval['approval_id'], True)
                                if result.get("status") == "approved":
                                    st.success(f"✅ Approved! Transfer completed.")
                                    st.rerun()
                                else:
                                    st.error(f"Error: {result}")
                        
                        with col_reject:
                            if st.button("❌ Reject", key=f"reject_{approval['approval_id']}"):
                                result = approve_transfer(approval['approval_id'], False)
                                if result.get("status") == "rejected":
                                    st.info(f"❌ Transfer rejected")
                                    st.rerun()
                                else:
                                    st.error(f"Error: {result}")


if __name__ == "__main__":
    main()
