"""
Production Streamlit UI with session management and workflow tracking.
Supports real-time approval notifications and status updates.
Cloud-ready with environment variable support.
"""
import os
import streamlit as st
import requests
from datetime import datetime

# Configure orchestrator URL (supports cloud deployment)
BASE_URL = os.environ.get("ORCHESTRATOR_URL", "http://localhost:8000")

# Add https:// scheme if not present (for Render deployment)
if BASE_URL and not BASE_URL.startswith(("http://", "https://")):
    BASE_URL = f"https://{BASE_URL}"

# Try Streamlit secrets as fallback (for Streamlit Cloud)
try:
    if not BASE_URL or BASE_URL == "http://localhost:8000":
        BASE_URL = st.secrets.get("ORCHESTRATOR_URL", BASE_URL)
except Exception:
    pass

# API endpoints
CHAT_URL = f"{BASE_URL}/chat"
APPROVALS_URL = f"{BASE_URL}/approvals/pending"
WORKFLOW_APPROVE_URL = f"{BASE_URL}/workflow/{{session_id}}/approve"
WORKFLOW_STATUS_URL = f"{BASE_URL}/workflow/{{session_id}}/status"
SESSIONS_URL = f"{BASE_URL}/sessions"


def send_message(message: str, session_id: str = None, user_id: str = "default_user"):
    """Send message to orchestrator with session tracking."""
    try:
        payload = {"message": message, "user_id": user_id}
        if session_id:
            payload["session_id"] = session_id
        
        r = requests.post(CHAT_URL, json=payload, timeout=10)
        return r.json()
    except Exception as e:
        return {"reply": {"error": str(e)}}


def get_pending_approvals():
    """Fetch pending approval requests."""
    try:
        r = requests.get(APPROVALS_URL, timeout=5)
        if r.status_code == 200:
            data = r.json()
            if isinstance(data, dict) and "pending_approvals" in data:
                return data["pending_approvals"]
            return data if isinstance(data, list) else []
        return []
    except Exception as e:
        st.error(f"Error fetching approvals: {e}")
        return []


def approve_transfer(session_id: str, approved: bool, approver_id: str = "manager@bank.com", reason: str = None):
    """Approve or reject a transfer via workflow endpoint."""
    try:
        url = WORKFLOW_APPROVE_URL.format(session_id=session_id)
        payload = {
            "approver_id": approver_id,
            "approved": approved
        }
        if reason:
            payload["reason"] = reason
        
        r = requests.post(url, json=payload, timeout=10)
        return r.json()
    except Exception as e:
        return {"error": str(e)}


def get_workflow_status(session_id: str):
    """Get workflow status for a session."""
    try:
        url = WORKFLOW_STATUS_URL.format(session_id=session_id)
        r = requests.get(url, timeout=5)
        if r.status_code == 200:
            return r.json()
        return None
    except Exception:
        return None


def format_timestamp(iso_timestamp: str) -> str:
    """Format ISO timestamp to readable format."""
    try:
        dt = datetime.fromisoformat(iso_timestamp.replace('Z', '+00:00'))
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except:
        return iso_timestamp


def format_response(reply: dict) -> str:
    """Format API response into user-friendly message."""
    if isinstance(reply, str):
        return reply
    
    if not isinstance(reply, dict):
        return str(reply)
    
    # Handle error responses
    if "error" in reply:
        return f"❌ Error: {reply['error']}"
    
    # Extract intent and data
    intent = reply.get('intent', '')
    status = reply.get('status', '')
    data = reply.get('data', {})
    
    # Balance inquiry
    if intent == 'balance_inquiry' and status == 'success':
        balance = data.get('balance', 0)
        return f"💰 Your current balance is **${balance:,.2f}**"
    
    # Transfer success (handle both 'transfer' and 'money_transfer' intents)
    if (intent in ['transfer', 'money_transfer']) and status == 'success':
        # Try to extract amount from various possible locations
        amount = data.get('amount') or data.get('transferAmount', 0)
        recipient = data.get('recipientAccount') or data.get('recipient', 'recipient')
        
        # Parse amount from message if not found
        if not amount and 'message' in data:
            import re
            match = re.search(r'(\d+\.?\d*)', data['message'])
            if match:
                amount = float(match.group(1))
        
        # Get approval type
        approved_by = reply.get('approved_by', '')
        approval_note = " (Auto-approved)" if approved_by == 'auto' else ""
        
        return f"✅ **Transfer successful!{approval_note}**\n\n${amount:,.2f} has been sent to {recipient}"
    
    # Statement (handle both 'statement' and 'account_statement' intents)
    if intent in ['statement', 'account_statement'] and status == 'success':
        # Check if we have structured transaction data
        transactions = data.get('transactions', [])
        if transactions:
            msg = f"📊 **Recent Transactions ({len(transactions)})**\n\n"
            for txn in transactions[:5]:  # Show first 5
                date = txn.get('date', 'N/A')
                desc = txn.get('description', 'N/A')
                amt = txn.get('amount', 0)
                msg += f"• {date}: {desc} - ${amt:,.2f}\n"
            return msg
        
        # Fallback: extract info from statement string
        statement_text = data.get('statement', '')
        if statement_text:
            import re
            # Extract balance from statement
            balance_match = re.search(r'Balance\s+(\d+\.?\d*)', statement_text)
            account_match = re.search(r'account\s+(\w+)', statement_text, re.IGNORECASE)
            
            account = account_match.group(1) if account_match else 'your account'
            balance = float(balance_match.group(1)) if balance_match else 0
            
            return f"📊 **Account Statement**\n\nAccount: {account}\nCurrent Balance: **${balance:,.2f}**"
        
        return "📊 No recent transactions found"
    
    # Loan information (handle both 'loan' and 'loan_inquiry' intents)
    if intent in ['loan', 'loan_inquiry'] and status == 'success':
        # Check for structured data
        loan_type = data.get('loanType')
        amount = data.get('amount', 0)
        interest = data.get('interestRate', 0)
        tenure = data.get('tenure', 0)
        
        if loan_type:
            return f"🏦 **Loan Information**\n\n**Type:** {loan_type}\n**Amount:** ${amount:,.2f}\n**Interest Rate:** {interest}%\n**Tenure:** {tenure} months"
        
        # Fallback: extract info from loan_info string
        loan_text = data.get('loan_info', '')
        if loan_text:
            import re
            # Extract eligible amount - look for patterns like "$100000.00", "100000", "$100,000"
            # Try to find amount after "up to" first (most specific)
            amount_match = re.search(r'up\s+to\s+\$?(\d+(?:,\d{3})*\.?\d*)', loan_text, re.IGNORECASE)
            if not amount_match:
                # Fallback to any dollar amount
                amount_match = re.search(r'\$(\d+(?:,\d{3})*\.?\d*)', loan_text)
            if not amount_match:
                # Last fallback to any number
                amount_match = re.search(r'(\d+(?:,\d{3})*\.?\d*)', loan_text)
            
            account_match = re.search(r'account\s+(\w+)', loan_text, re.IGNORECASE)
            
            account = account_match.group(1) if account_match else 'your account'
            eligible_amount = amount_match.group(1).replace(',', '') if amount_match else '0'
            eligible_amount = float(eligible_amount)
            
            return f"🏦 **Loan Information**\n\nAccount: {account}\nYou are eligible for a loan up to **${eligible_amount:,.2f}**"
        
        return "🏦 Loan information not available"
    
    # Pending approval
    if status == 'PENDING_APPROVAL':
        return reply  # Keep existing approval format
    
    # Default: return the message or full dict
    if 'message' in reply:
        return reply['message']
    
    return str(reply)


def main():
    st.set_page_config(
        page_title="Banking AI POC v2.0",
        page_icon="🏦",
        layout="wide"
    )
    
    # Custom CSS for banking blue and white theme
    st.markdown("""
        <style>
        /* Main background */
        .stApp {
            background: linear-gradient(135deg, #003d82 0%, #0055b8 100%);
        }
        
        /* Sidebar styling */
        [data-testid="stSidebar"] {
            background-color: #ffffff;
            border-right: 3px solid #003d82;
        }
        
        /* Headers */
        h1, h2, h3 {
            color: #ffffff !important;
        }
        
        /* Sidebar headers */
        [data-testid="stSidebar"] h1,
        [data-testid="stSidebar"] h2,
        [data-testid="stSidebar"] h3 {
            color: #003d82 !important;
        }
        
        /* Chat containers - transparent with blue tint */
        .stChatMessage {
            background-color: rgba(255, 255, 255, 0.15);
            border-radius: 10px;
            padding: 15px;
            margin: 10px 0;
            box-shadow: 0 2px 8px rgba(0, 61, 130, 0.3);
            border: 1px solid rgba(255, 255, 255, 0.3);
        }
        
        /* Chat message text - black color */
        .stChatMessage p,
        .stChatMessage span,
        .stChatMessage div {
            color: #000000 !important;
        }
        
        /* Input boxes */
        .stTextInput input {
            background-color: rgba(255, 255, 255, 0.9);
            border: 2px solid #003d82;
            border-radius: 5px;
            color: #000000;
        }
        
        /* Buttons */
        .stButton button {
            background-color: #003d82;
            color: white;
            border-radius: 5px;
            border: none;
            font-weight: 600;
        }
        
        .stButton button:hover {
            background-color: #0055b8;
        }
        
        /* Metrics */
        [data-testid="stMetricValue"] {
            color: #003d82;
        }
        
        /* Success/Info boxes - transparent blue */
        .stSuccess {
            background-color: rgba(232, 244, 248, 0.3);
            color: #ffffff;
            border-left: 4px solid #0055b8;
        }
        
        .stInfo {
            background-color: rgba(240, 248, 255, 0.2);
            color: #ffffff;
            border-left: 4px solid #ffffff;
        }
        
        /* Expander */
        .streamlit-expanderHeader {
            background-color: rgba(255, 255, 255, 0.2);
            color: #ffffff;
            border-radius: 5px;
        }
        
        /* Text color adjustments */
        p, label, .stMarkdown {
            color: #ffffff;
        }
        
        [data-testid="stSidebar"] p,
        [data-testid="stSidebar"] label,
        [data-testid="stSidebar"] .stMarkdown {
            color: #003d82;
        }
        
        /* Form styling - transparent with blue tint */
        [data-testid="stForm"] {
            background-color: rgba(255, 255, 255, 0.15);
            border-radius: 10px;
            padding: 20px;
            border: 2px solid rgba(255, 255, 255, 0.3);
        }
        
        /* Form text to black */
        [data-testid="stForm"] label,
        [data-testid="stForm"] p {
            color: #000000 !important;
        }
        
        /* Caption text */
        .stCaption {
            color: #e0e0e0;
        }
        
        [data-testid="stSidebar"] .stCaption {
            color: #666666;
        }
        
        /* Message containers */
        [data-testid="stVerticalBlock"] > div {
            color: #000000;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # Initialize session state
    if "messages" not in st.session_state:
        st.session_state["messages"] = []
    if "session_id" not in st.session_state:
        st.session_state["session_id"] = None
    if "user_id" not in st.session_state:
        st.session_state["user_id"] = "default_user"
    
    # Check for pending approvals
    approvals = get_pending_approvals()
    show_approval_panel = len(approvals) > 0 or st.session_state.get("pending_approval_triggered", False)
    
    # Header
    st.title("🏦 Banking AI — Production Workflow Engine")
    
    # Session info in sidebar
    with st.sidebar:
        st.header("📊 Session Info")
        
        if st.session_state["session_id"]:
            st.success(f"**Session ID:** `{st.session_state['session_id'][:8]}...`")
            
            # Get workflow status
            status = get_workflow_status(st.session_state["session_id"])
            if status:
                st.metric("Status", status["status"].upper())
                st.metric("Executions", status["execution_count"])
                st.metric("Checkpoints", status["checkpoints"])
                
                with st.expander("📜 Execution Details"):
                    st.write(f"**User:** {status['user_id']}")
                    st.write(f"**Current Node:** {status.get('current_node', 'N/A')}")
                    st.write(f"**Created:** {format_timestamp(status['metadata']['created_at'])}")
                    st.write(f"**Last Activity:** {format_timestamp(status['metadata']['last_activity'])}")
        else:
            st.info("No active session")
        
        st.divider()
        
        st.header("ℹ️ Features")
        st.write("✅ State Checkpointing")
        st.write("✅ Human-in-the-Loop")
        st.write("✅ Session Management")
        st.write("✅ Workflow Resume")
        st.write("✅ Idempotent Execution")
        
        st.divider()
        
        if st.button("🔄 New Session", type="primary", use_container_width=True):
            st.session_state["session_id"] = None
            st.session_state["messages"] = []
            st.session_state.pop("pending_approval_triggered", None)
            st.rerun()
    
    # Create dynamic columns based on approvals
    if show_approval_panel:
        col1, col2 = st.columns([2, 1])
    else:
        col1 = st.container()
    
    with col1:
        st.header("💬 Chat Interface")
        
        # Chat input form
        with st.form(key="msg_form", clear_on_submit=True):
            user_input = st.text_input(
                "Your message",
                placeholder="Try: 'What's my balance?' or 'Transfer 6000 to Kiran'",
                key="user_input"
            )
            
            col_send, col_examples = st.columns([1, 3])
            
            with col_send:
                submitted = st.form_submit_button("Send", type="primary", use_container_width=True)
            
            with col_examples:
                st.caption("💡 Examples: balance | transfer 1000 to kiran | statement | loan info")
        
        if submitted and user_input:
            # Add user message
            st.session_state["messages"].append({
                "role": "user",
                "text": user_input,
                "timestamp": datetime.now().isoformat()
            })
            
            # Send to orchestrator
            response = send_message(
                user_input,
                session_id=st.session_state["session_id"],
                user_id=st.session_state["user_id"]
            )
            
            # Update session ID
            if "session_id" in response:
                st.session_state["session_id"] = response["session_id"]
            
            # Handle response
            reply = response.get("reply", {})
            
            # Check for pending approval
            if isinstance(reply, dict) and reply.get("status") == "PENDING_APPROVAL":
                st.session_state["pending_approval_triggered"] = True
                message_text = f"⏳ {reply.get('message', 'Transfer requires approval')}\n\n"
                message_text += f"**Amount:** ${reply.get('amount', 0):,.2f}\n"
                message_text += f"**Recipient:** {reply.get('recipient', 'N/A')}\n"
                message_text += f"**Approval ID:** `{reply.get('approval_id', 'N/A')}`"
            else:
                # Format response to user-friendly message
                message_text = format_response(reply)
            
            st.session_state["messages"].append({
                "role": "assistant",
                "text": message_text,
                "timestamp": datetime.now().isoformat(),
                "metadata": response
            })
            
            st.rerun()
        
        # Display conversation
        st.divider()
        
        for msg in st.session_state["messages"]:
            timestamp = format_timestamp(msg.get("timestamp", ""))
            
            if msg["role"] == "user":
                with st.chat_message("user"):
                    st.write(msg["text"])
                    st.caption(f"🕐 {timestamp}")
            else:
                with st.chat_message("assistant"):
                    st.write(msg["text"])
                    st.caption(f"🕐 {timestamp}")
                    
                    # Show execution history if available
                    if "metadata" in msg and "execution_history" in msg["metadata"]:
                        history = msg["metadata"]["execution_history"]
                        if history:
                            with st.expander("🔍 Execution Trace"):
                                for i, node in enumerate(history, 1):
                                    st.text(f"{i}. {node.get('node_id', 'unknown')}")
    
    # Approval panel (conditional)
    if show_approval_panel:
        with col2:
            st.header("⚠️ Pending Approvals")
            
            if st.session_state.get("pending_approval_triggered"):
                st.info("🔔 New approval request!")
            
            if st.button("🔄 Refresh", use_container_width=True):
                st.session_state.pop("pending_approval_triggered", None)
                st.rerun()
            
            st.divider()
            
            if not approvals:
                if st.session_state.get("pending_approval_triggered"):
                    with st.spinner("Loading approvals..."):
                        st.empty()
                else:
                    st.success("✅ No pending approvals")
            else:
                st.warning(f"📋 {len(approvals)} transfer(s) awaiting approval")
                st.session_state.pop("pending_approval_triggered", None)
                
                for approval in approvals:
                    approval_session_id = approval["session_id"]
                    
                    with st.expander(
                        f"💰 ${approval['amount']:,.2f} → {approval['recipient']}",
                        expanded=True
                    ):
                        st.metric("Amount", f"${approval['amount']:,.2f}")
                        st.write(f"**To:** {approval['recipient']}")
                        st.write(f"**Requested:** {format_timestamp(approval['requested_at'])}")
                        
                        # Show request details
                        if 'request_data' in approval:
                            request = approval['request_data']
                            if 'fromAccount' in request:
                                st.write(f"**From:** {request['fromAccount']}")
                        
                        st.caption(f"**Session:** `{approval_session_id[:12]}...`")
                        st.caption(f"**Approval ID:** `{approval['approval_id'][:12]}...`")
                        
                        st.divider()
                        
                        col_approve, col_reject = st.columns(2)
                        
                        with col_approve:
                            if st.button(
                                "✅ Approve",
                                key=f"approve_{approval['approval_id']}",
                                type="primary",
                                use_container_width=True
                            ):
                                with st.spinner("Approving..."):
                                    result = approve_transfer(approval_session_id, True)
                                
                                if result.get("status") == "approved":
                                    st.success("✅ Approved & Executed!")
                                    
                                    # Add system message to chat
                                    st.session_state["messages"].append({
                                        "role": "assistant",
                                        "text": f"✅ Transfer approved and executed:\n${approval['amount']:,.2f} → {approval['recipient']}",
                                        "timestamp": datetime.now().isoformat()
                                    })
                                    
                                    st.rerun()
                                else:
                                    st.error(f"Error: {result.get('error', 'Unknown error')}")
                        
                        with col_reject:
                            if st.button(
                                "❌ Reject",
                                key=f"reject_{approval['approval_id']}",
                                use_container_width=True
                            ):
                                reason = st.text_input(
                                    "Rejection reason:",
                                    key=f"reason_{approval['approval_id']}"
                                )
                                
                                with st.spinner("Rejecting..."):
                                    result = approve_transfer(
                                        approval_session_id,
                                        False,
                                        reason=reason or "Rejected by manager"
                                    )
                                
                                if result.get("status") == "rejected":
                                    st.info("❌ Transfer rejected")
                                    
                                    # Add system message to chat
                                    st.session_state["messages"].append({
                                        "role": "assistant",
                                        "text": f"❌ Transfer rejected:\n${approval['amount']:,.2f} → {approval['recipient']}\nReason: {reason}",
                                        "timestamp": datetime.now().isoformat()
                                    })
                                    
                                    st.rerun()
                                else:
                                    st.error(f"Error: {result.get('error', 'Unknown error')}")


if __name__ == "__main__":
    main()
