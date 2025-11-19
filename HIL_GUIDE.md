# Human-in-the-Loop (HIL) Approval System

## Overview

The Banking AI POC now includes **persistence and Human-in-the-Loop (HIL) approval** for high-value transactions.

### Key Features
- ✅ **Automatic detection** of high-value transfers (>$5,000)
- ✅ **SQLite persistence** for workflow state and approval tracking
- ✅ **Session management** for multi-turn conversations
- ✅ **Approval API** for programmatic approvals
- ✅ **Audit trail** of all approval requests

---

## How It Works

### 1. High-Value Transfer Detection

When a user requests a transfer > $5,000:
```
User: "Transfer 10000 to Kiran"
```

The system:
1. Creates a workflow session
2. Generates an approval request
3. Saves state to database
4. Returns approval ID to user

Response:
```json
{
  "status": "pending_approval",
  "message": "Transfer of $10000 to kiran requires approval. Approval ID: abc-123",
  "approval_id": "abc-123",
  "session_id": "xyz-789",
  "amount": 10000,
  "recipient": "kiran"
}
```

### 2. Approval Workflow

**View pending approvals:**
```bash
GET http://localhost:8000/approvals/pending
```

Response:
```json
{
  "pending_approvals": [
    {
      "approval_id": "abc-123",
      "session_id": "xyz-789",
      "workflow_type": "money_transfer",
      "amount": 10000,
      "recipient": "kiran",
      "requested_at": "2025-11-19T10:30:00"
    }
  ]
}
```

**Approve a transfer:**
```bash
POST http://localhost:8000/approve
Content-Type: application/json

{
  "approval_id": "abc-123",
  "approved": true,
  "approver_id": "manager@bank.com"
}
```

Response:
```json
{
  "status": "approved",
  "approval_id": "abc-123",
  "session_id": "xyz-789",
  "transfer_result": {
    "success": true,
    "message": "Transfer completed"
  }
}
```

**Reject a transfer:**
```bash
POST http://localhost:8000/approve
Content-Type: application/json

{
  "approval_id": "abc-123",
  "approved": false,
  "rejection_reason": "Insufficient documentation",
  "approver_id": "manager@bank.com"
}
```

### 3. Session Tracking

**Check session status:**
```bash
GET http://localhost:8000/session/xyz-789
```

Response:
```json
{
  "session_id": "xyz-789",
  "user_id": "default_user",
  "workflow_type": "banking",
  "status": "pending_approval",
  "created_at": "2025-11-19T10:30:00",
  "updated_at": "2025-11-19T10:30:05"
}
```

---

## Configuration

### Threshold Settings

Edit `ai-orchestrator/agent.py`:
```python
# HIL approval threshold
HIGH_VALUE_THRESHOLD = 5000.0  # Change this value
```

### Database Location

Default: `ai-orchestrator/workflows.db` (SQLite)

For production, upgrade to PostgreSQL:
```python
# In persistence.py
def __init__(self, db_path: str = "postgresql://user:pass@localhost/workflows"):
    # Use SQLAlchemy for PostgreSQL support
```

---

## API Endpoints

### Chat Endpoint (with session tracking)
```http
POST /chat
Content-Type: application/json

{
  "message": "Transfer 10000 to Kiran",
  "session_id": "optional-session-id",
  "user_id": "user@example.com"
}
```

### Approval Endpoint
```http
POST /approve
Content-Type: application/json

{
  "approval_id": "abc-123",
  "approved": true|false,
  "approver_id": "manager@example.com",
  "rejection_reason": "Optional reason if rejected"
}
```

### Pending Approvals
```http
GET /approvals/pending
```

### Session Status
```http
GET /session/{session_id}
```

---

## Testing the HIL Flow

### Test 1: Low-Value Transfer (Auto-Approved)
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Transfer 1000 to Kiran"}'
```

Expected: Transfer executes immediately (no approval needed)

### Test 2: High-Value Transfer (Requires Approval)
```bash
# Step 1: Request transfer
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Transfer 10000 to Kiran"}'

# Response will include approval_id: "abc-123"

# Step 2: View pending approvals
curl http://localhost:8000/approvals/pending

# Step 3: Approve the transfer
curl -X POST http://localhost:8000/approve \
  -H "Content-Type: application/json" \
  -d '{
    "approval_id": "abc-123",
    "approved": true,
    "approver_id": "manager@bank.com"
  }'
```

---

## Database Schema

### workflow_sessions
```sql
CREATE TABLE workflow_sessions (
    session_id TEXT PRIMARY KEY,
    user_id TEXT,
    workflow_type TEXT,
    state TEXT,
    status TEXT,
    created_at TEXT,
    updated_at TEXT
)
```

### pending_approvals
```sql
CREATE TABLE pending_approvals (
    approval_id TEXT PRIMARY KEY,
    session_id TEXT,
    workflow_type TEXT,
    request_data TEXT,
    status TEXT,
    amount REAL,
    recipient TEXT,
    requested_at TEXT,
    approved_at TEXT,
    approver_id TEXT,
    rejection_reason TEXT,
    FOREIGN KEY (session_id) REFERENCES workflow_sessions(session_id)
)
```

---

## Building an Approval Dashboard

### Example Streamlit Approval UI

```python
import streamlit as st
import requests

API_URL = "http://localhost:8000"

st.title("Transfer Approval Dashboard")

# Get pending approvals
response = requests.get(f"{API_URL}/approvals/pending")
pending = response.json()["pending_approvals"]

if not pending:
    st.info("No pending approvals")
else:
    for approval in pending:
        with st.expander(f"${approval['amount']} to {approval['recipient']}"):
            st.write(f"**Approval ID:** {approval['approval_id']}")
            st.write(f"**Requested:** {approval['requested_at']}")
            
            col1, col2 = st.columns(2)
            
            if col1.button("✅ Approve", key=f"approve_{approval['approval_id']}"):
                requests.post(f"{API_URL}/approve", json={
                    "approval_id": approval['approval_id'],
                    "approved": True,
                    "approver_id": st.session_state.get("user", "admin")
                })
                st.success("Approved!")
                st.rerun()
            
            if col2.button("❌ Reject", key=f"reject_{approval['approval_id']}"):
                reason = st.text_input("Reason", key=f"reason_{approval['approval_id']}")
                requests.post(f"{API_URL}/approve", json={
                    "approval_id": approval['approval_id'],
                    "approved": False,
                    "rejection_reason": reason,
                    "approver_id": st.session_state.get("user", "admin")
                })
                st.error("Rejected")
                st.rerun()
```

---

## Production Considerations

### 1. Notifications
Add email/SMS alerts when approval is needed:
```python
from sendgrid import SendGridAPIClient

def send_approval_notification(approval_data):
    sg = SendGridAPIClient(api_key=os.getenv('SENDGRID_API_KEY'))
    sg.send({
        "to": "approver@bank.com",
        "subject": f"Approval Required: ${approval_data['amount']}",
        "body": f"Transfer to {approval_data['recipient']} needs approval"
    })
```

### 2. Timeout Handling
Auto-expire old approvals:
```python
# Add to persistence.py
def expire_old_approvals(hours=24):
    cutoff = datetime.now() - timedelta(hours=hours)
    # Update status to 'expired' for old pending approvals
```

### 3. Audit Logging
Log all approval actions:
```python
import logging

logger.info(f"Approval {approval_id} {action} by {approver_id} at {timestamp}")
```

### 4. Role-Based Access
Different approval limits per role:
```python
APPROVAL_LIMITS = {
    "teller": 1000,
    "manager": 10000,
    "director": 100000
}
```

---

## Benefits

✅ **Compliance** - Audit trail of all high-value transactions  
✅ **Risk Management** - Human oversight for large transfers  
✅ **Flexibility** - Configurable thresholds and workflows  
✅ **Resumability** - Workflows can pause and resume  
✅ **Scalability** - Database-backed persistence  

---

## Next Steps

1. **Deploy approval dashboard** - Streamlit or React UI
2. **Add notifications** - Email/SMS when approval needed
3. **Implement RBAC** - Role-based approval limits
4. **Add timeouts** - Auto-expire old approvals
5. **Upgrade to PostgreSQL** - For production scale
6. **Add audit reports** - Compliance and reporting

---

**Repository:** https://github.com/Dhanusankar/Banking  
**Status:** ✅ HIL and persistence implemented and pushed
