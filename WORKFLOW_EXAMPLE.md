# 🚀 Production Workflow Engine - Complete Example

## Example: "Transfer 6000 to Kiran" with HIL Approval

This document demonstrates the complete end-to-end flow of a high-value transfer with Human-in-the-Loop approval, showing all checkpoints, state transitions, and system interactions.

---

## 🎯 Overview

**Scenario:** User requests to transfer $6000 to Kiran (above $5000 threshold)

**Expected Behavior:**
1. Workflow pauses at HIL node
2. Manager receives approval request  
3. Upon approval, workflow resumes and executes transfer
4. All state preserved across pause/resume

---

## 📊 Complete Workflow Trace

### **Step 1: User Initiates Transfer**

**Action:** User types in Streamlit UI
```
Transfer 6000 to Kiran
```

**UI → Orchestrator:**
```http
POST /chat
Content-Type: application/json

{
  "message": "Transfer 6000 to Kiran",
  "user_id": "default_user",
  "session_id": null
}
```

---

### **Step 2: Session Creation**

**Orchestrator (session_manager.py):**
```python
session = session_manager.create_session(
    user_id="default_user",
    workflow_type="banking"
)
# Generates: session_id = "a1b2c3d4-5678-90ab-cdef-1234567890ab"
```

**Console Output:**
```
✓ Session created: a1b2c3d4... (user: default_user)
```

**Initial State Created:**
```json
{
  "message": "Transfer 6000 to Kiran",
  "user_id": "default_user",
  "session_id": "a1b2c3d4-5678-90ab-cdef-1234567890ab",
  "from_account": "123",
  "execution_history": []
}
```

---

### **Step 3: Graph Execution Begins**

**Entry Point:** `validate_input` node

**Node: validate_input_node**
```python
# Classify intent
intent = classify_intent("Transfer 6000 to Kiran")
# Returns: "money_transfer"
```

**Checkpoint Saved:**
```
📝 Checkpoint: validate_input_start
Session: a1b2c3d4...
Node: validate_input
State: {intent: null, ...}
```

**State After Validation:**
```json
{
  "message": "Transfer 6000 to Kiran",
  "intent": "money_transfer",
  "session_id": "a1b2c3d4-5678-90ab-cdef-1234567890ab",
  "execution_history": ["validate_input"]
}
```

**Checkpoint Saved:**
```
✓ Checkpoint saved: validate_input (session: a1b2c3d4...)
```

**Console Output:**
```
📋 Intent classified: money_transfer
```

---

### **Step 4: Route to Transfer Preparation**

**Conditional Edge:** `route_by_intent()`
```python
# Routes to: "money_transfer_prepare"
```

**Node: money_transfer_prepare_node**
```python
# Extract transfer details
details = extract_transfer_details("Transfer 6000 to Kiran")
# Returns: {"amount": 6000, "recipient": "kiran"}
```

**Checkpoint Saved:**
```
📝 Checkpoint: money_transfer_prepare_start
```

**State After Preparation:**
```json
{
  "intent": "money_transfer",
  "amount": 6000.0,
  "recipient": "kiran",
  "from_account": "123",
  "request_data": {
    "fromAccount": "123",
    "toAccount": "kiran",
    "amount": 6000.0
  },
  "execution_history": ["validate_input", "money_transfer_prepare"]
}
```

**Checkpoint Saved:**
```
✓ Checkpoint saved: money_transfer_prepare (session: a1b2c3d4...)
```

**Console Output:**
```
💰 Transfer prepared: $6000.0 → kiran
```

---

### **Step 5: HIL Approval Check**

**Node: money_transfer_hil_node**

**HIL Threshold Check:**
```python
needs_approval = (6000.0 >= 5000.0)  # TRUE - requires approval
```

**HIL Node Execution:**
```python
hil_result = transfer_hil_node.execute(
    state={
        "amount": 6000.0,
        "recipient": "kiran",
        "request_data": {...}
    },
    session_id="a1b2c3d4...",
    user_id="default_user"
)
```

**Checkpoint Saved by HIL:**
```
✓ Checkpoint saved: transfer_approval (session: a1b2c3d4...)
Metadata: {
  "user_id": "default_user",
  "approval_message": "Transfer requires approval (threshold: $5000)",
  "paused_at": "2025-11-19T10:30:45.123456"
}
```

**Approval Request Created in Database:**
```sql
INSERT INTO pending_approvals (
  approval_id,
  session_id,
  workflow_type,
  request_data,
  status,
  amount,
  recipient,
  requested_at
) VALUES (
  'f9e8d7c6-5b4a-3c2d-1e0f-9a8b7c6d5e4f',
  'a1b2c3d4-5678-90ab-cdef-1234567890ab',
  'banking',
  '{"fromAccount":"123","toAccount":"kiran","amount":6000.0}',
  'pending',
  6000.0,
  'kiran',
  '2025-11-19T10:30:45.123456'
)
```

**Session Status Updated:**
```python
persistence.save_state(
    session_id="a1b2c3d4...",
    state={...},
    status="pending_approval"
)
```

**Console Output:**
```
⏸️  Transfer paused for approval: $6000.0
```

**HIL Result:**
```json
{
  "status": "PENDING_APPROVAL",
  "message": "Transfer requires approval (threshold: $5000)",
  "session_id": "a1b2c3d4-5678-90ab-cdef-1234567890ab",
  "approval_id": "f9e8d7c6-5b4a-3c2d-1e0f-9a8b7c6d5e4f",
  "checkpoint_id": "12345678-abcd-efgh-ijkl-mnopqrstuvwx",
  "node_id": "transfer_approval",
  "amount": 6000.0,
  "recipient": "kiran",
  "paused_at": "2025-11-19T10:30:45.123456"
}
```

**Workflow Halts:**
```python
state["_halt"] = True  # Signals graph to stop
return END
```

---

### **Step 6: Response to User**

**Orchestrator → UI:**
```json
{
  "reply": {
    "status": "PENDING_APPROVAL",
    "message": "Transfer requires approval (threshold: $5000)",
    "session_id": "a1b2c3d4-5678-90ab-cdef-1234567890ab",
    "approval_id": "f9e8d7c6-5b4a-3c2d-1e0f-9a8b7c6d5e4f",
    "amount": 6000.0,
    "recipient": "kiran"
  },
  "session_id": "a1b2c3d4-5678-90ab-cdef-1234567890ab",
  "status": "PENDING_APPROVAL"
}
```

**UI Display:**
```
🤖 Assistant:
⏳ Transfer requires approval (threshold: $5000)

**Amount:** $6,000.00
**Recipient:** kiran
**Approval ID:** `f9e8d7c6-5b4a-3c2d-1e0f`
```

**Approval Panel Appears:**
```
⚠️ Pending Approvals
🔔 New approval request!

📋 1 transfer(s) awaiting approval

┌─────────────────────────────────────┐
│ 💰 $6,000.00 → kiran                │
│                                     │
│ Amount: $6,000.00                   │
│ To: kiran                           │
│ From: 123                           │
│ Requested: 2025-11-19 10:30:45      │
│ Session: `a1b2c3d4...`              │
│ Approval ID: `f9e8d7c6...`          │
│                                     │
│ [✅ Approve]  [❌ Reject]            │
└─────────────────────────────────────┘
```

---

### **Step 7: Manager Reviews and Approves**

**Action:** Manager clicks **✅ Approve** button

**UI → Orchestrator:**
```http
POST /workflow/a1b2c3d4-5678-90ab-cdef-1234567890ab/approve
Content-Type: application/json

{
  "approver_id": "manager@bank.com",
  "approved": true
}
```

---

### **Step 8: Approval Processing**

**Orchestrator (server_v2.py):**

**1. Load Session:**
```python
session = session_manager.get_session("a1b2c3d4...")
# Verifies: session.status == SessionStatus.PENDING_APPROVAL
```

**2. Approve via HIL Node:**
```python
hil_result = transfer_hil_node.approve(
    session_id="a1b2c3d4...",
    approver_id="manager@bank.com",
    reason=None
)
```

**3. Load Checkpoint:**
```python
checkpoint = checkpoint_store.load_checkpoint("a1b2c3d4...")
```

**Checkpoint Data Retrieved:**
```json
{
  "checkpoint_id": "12345678-abcd-efgh-ijkl-mnopqrstuvwx",
  "node_id": "transfer_approval",
  "state": {
    "message": "Transfer 6000 to Kiran",
    "intent": "money_transfer",
    "amount": 6000.0,
    "recipient": "kiran",
    "from_account": "123",
    "request_data": {
      "fromAccount": "123",
      "toAccount": "kiran",
      "amount": 6000.0
    }
  },
  "metadata": {
    "user_id": "default_user",
    "approval_message": "...",
    "paused_at": "2025-11-19T10:30:45.123456"
  },
  "created_at": "2025-11-19T10:30:45.123456"
}
```

**Console Output:**
```
✓ Checkpoint loaded: transfer_approval (session: a1b2c3d4...)
```

**4. Update Approval in Database:**
```sql
UPDATE pending_approvals 
SET 
  status = 'approved',
  approver_id = 'manager@bank.com',
  approved_at = '2025-11-19T10:32:15.789012'
WHERE approval_id = 'f9e8d7c6-5b4a-3c2d-1e0f-9a8b7c6d5e4f'
```

**5. Update State with Approval Decision:**
```python
state['hil_decision'] = {
    "approved": True,
    "approver_id": "manager@bank.com",
    "reason": None,
    "approved_at": "2025-11-19T10:32:15.789012"
}
```

**6. Save New Checkpoint:**
```
✓ Checkpoint saved: transfer_approval_approved (session: a1b2c3d4...)
```

---

### **Step 9: Workflow Resumes - Transfer Execution**

**Function Call:**
```python
workflow_result = resume_workflow(
    session_id="a1b2c3d4...",
    user_action="approved"
)
```

**Console Output:**
```
🔄 Resuming workflow: a1b2c3d4... (action: approved)
```

**Node: money_transfer_execute_node**

**1. Verify Approval:**
```python
hil_decision = state.get("hil_decision", {})
assert hil_decision.get("approved") == True
```

**2. Execute Transfer:**
```python
request_data = {
    "fromAccount": "123",
    "toAccount": "kiran",
    "amount": 6000.0
}
```

**Orchestrator → Backend:**
```http
POST http://localhost:8081/api/transfer
Content-Type: application/json

{
  "fromAccount": "123",
  "toAccount": "kiran",
  "amount": 6000.0
}
```

**Backend Processing:**
```java
// BankService.java
public TransferResponse transfer(TransferRequest req) {
    Account from = accounts.get("123");  // Balance: 50000.0
    Account to = accounts.get("kiran");  // Balance: 1000.0
    
    // Validate
    if (from.getBalance() < 6000.0) {
        return new TransferResponse(false, "Insufficient funds");
    }
    
    // Execute transfer
    from.setBalance(50000.0 - 6000.0);  // New: 44000.0
    to.setBalance(1000.0 + 6000.0);     // New: 7000.0
    
    return new TransferResponse(
        true,
        "Transferred 6000.00 from 123 to kiran"
    );
}
```

**Backend → Orchestrator:**
```json
{
  "success": true,
  "message": "Transferred 6000.00 from 123 to kiran"
}
```

**Console Output:**
```
✓ Transfer executed: $6000.0 → kiran
```

**3. Update State:**
```python
state["response"] = {
    "intent": "money_transfer",
    "status": "success",
    "data": {
        "success": true,
        "message": "Transferred 6000.00 from 123 to kiran"
    },
    "approved_by": "manager@bank.com"
}
```

**4. Save Final Checkpoint:**
```
✓ Checkpoint saved: money_transfer_execute (session: a1b2c3d4...)
```

---

### **Step 10: Session Completion**

**Update Session:**
```python
session.set_status(SessionStatus.APPROVED)
session.add_message(
    "system",
    "Transfer approved by manager@bank.com",
    metadata={"approver_id": "manager@bank.com"}
)
session_manager.save_session(session)
```

**Final Session State:**
```json
{
  "session_id": "a1b2c3d4-5678-90ab-cdef-1234567890ab",
  "user_id": "default_user",
  "workflow_type": "banking",
  "status": "approved",
  "conversation_history": [
    {
      "role": "user",
      "content": "Transfer 6000 to Kiran",
      "timestamp": "2025-11-19T10:30:44.000000"
    },
    {
      "role": "system",
      "content": "Transfer approved by manager@bank.com",
      "timestamp": "2025-11-19T10:32:16.000000"
    }
  ],
  "workflow_state": {
    "intent": "money_transfer",
    "amount": 6000.0,
    "recipient": "kiran",
    "from_account": "123",
    "hil_decision": {
      "approved": true,
      "approver_id": "manager@bank.com"
    },
    "response": {
      "status": "success",
      "data": {...}
    }
  },
  "current_node": "money_transfer_execute",
  "execution_count": 1
}
```

**Console Output:**
```
✓ Session saved: a1b2c3d4...
```

---

### **Step 11: Response to Manager**

**Orchestrator → UI:**
```json
{
  "status": "approved",
  "session_id": "a1b2c3d4-5678-90ab-cdef-1234567890ab",
  "result": {
    "intent": "money_transfer",
    "status": "success",
    "data": {
      "success": true,
      "message": "Transferred 6000.00 from 123 to kiran"
    },
    "approved_by": "manager@bank.com"
  },
  "approved_by": "manager@bank.com"
}
```

**UI Display:**
```
✅ Approved & Executed!

🤖 Assistant:
✅ Transfer approved and executed:
$6,000.00 → kiran
```

**Approval Panel:**
```
⚠️ Pending Approvals
✅ No pending approvals
```

---

## 📋 Complete Checkpoint Timeline

| # | Checkpoint ID | Node | State Key Fields | Timestamp |
|---|---------------|------|------------------|-----------|
| 1 | `cp-001` | `validate_input_start` | intent: null | 10:30:44.100 |
| 2 | `cp-002` | `validate_input_end` | intent: money_transfer | 10:30:44.250 |
| 3 | `cp-003` | `money_transfer_prepare_start` | amount: null | 10:30:44.300 |
| 4 | `cp-004` | `money_transfer_prepare_end` | amount: 6000, request_data: {...} | 10:30:44.450 |
| 5 | `cp-005` | `transfer_approval` | paused, status: PENDING_APPROVAL | 10:30:45.123 |
| 6 | `cp-006` | `transfer_approval_approved` | hil_decision: approved | 10:32:15.789 |
| 7 | `cp-007` | `money_transfer_execute_end` | response: success | 10:32:16.123 |

---

## 🗄️ Database State After Completion

### `workflow_sessions` Table:
```
session_id: a1b2c3d4-5678-90ab-cdef-1234567890ab
user_id: default_user
workflow_type: banking
status: approved
created_at: 2025-11-19T10:30:44
updated_at: 2025-11-19T10:32:16
```

### `pending_approvals` Table:
```
approval_id: f9e8d7c6-5b4a-3c2d-1e0f-9a8b7c6d5e4f
session_id: a1b2c3d4-5678-90ab-cdef-1234567890ab
status: approved
amount: 6000.0
recipient: kiran
approver_id: manager@bank.com
requested_at: 2025-11-19T10:30:45
approved_at: 2025-11-19T10:32:15
```

### `checkpoints` Table:
```
7 checkpoints saved for session a1b2c3d4...
Latest: money_transfer_execute_end
Status: completed
```

---

## 🎯 Key Features Demonstrated

### ✅ **State Persistence**
- All workflow state saved at each node
- Can resume from any checkpoint
- State preserved across process restarts

### ✅ **Human-in-the-Loop**
- Automatic threshold detection ($5000)
- Workflow pauses at HIL node
- Manager approval required to continue
- Complete audit trail

### ✅ **Checkpointing**
- 7 checkpoints saved throughout execution
- Node-level granularity
- Automatic save/restore

### ✅ **Session Management**
- Unique session per conversation
- Conversation history maintained
- Idempotent execution tracking

### ✅ **Resume Logic**
- Load checkpoint with full state
- Apply approval decision
- Continue from paused node
- Execute remaining workflow

---

## 🔄 Low-Value Transfer (< $5000)

For comparison, here's what happens with a transfer below the threshold:

**User Input:** `Transfer 2000 to Kiran`

**Execution:**
1. ✅ validate_input → intent: money_transfer
2. ✅ money_transfer_prepare → amount: 2000, recipient: kiran
3. ✅ money_transfer_hil → **BYPASSED** (below threshold)
4. ✅ money_transfer_execute → Transfer executed immediately

**Result:**
```json
{
  "intent": "money_transfer",
  "status": "success",
  "data": {
    "success": true,
    "message": "Transferred 2000.00 from 123 to kiran"
  },
  "hil_decision": {
    "approved": true,
    "auto": true
  }
}
```

**No approval required!** Transfer executes in < 1 second.

---

## 📊 Architecture Benefits

### **Scalability**
- Stateless orchestrator (state in DB/Redis)
- Horizontal scaling possible
- Session-based load distribution

### **Reliability**
- Checkpoint recovery on failures
- Idempotent operations
- Complete audit trail

### **Flexibility**
- Easy to add new approval rules
- Configurable thresholds
- Extensible node system

### **Observability**
- Full execution trace
- Checkpoint history
- Conversation logs

---

## 🚀 Production Deployment

### **Required Services:**
1. **Backend (Java):** Port 8081
2. **Orchestrator (Python):** Port 8000
3. **UI (Streamlit):** Port 8501
4. **Database:** SQLite (dev) or PostgreSQL (prod)
5. **Cache (Optional):** Redis for checkpoints

### **Environment Variables:**
```bash
BACKEND_URL=http://localhost:8081
ORCHESTRATOR_URL=http://localhost:8000
DATABASE_URL=sqlite:///workflows.db
REDIS_URL=redis://localhost:6379
HIL_THRESHOLD=5000.0
```

### **Startup Commands:**
```bash
# Terminal 1: Backend
cd backend-java/banking-backend
mvn spring-boot:run

# Terminal 2: Orchestrator (NEW VERSION)
cd ai-orchestrator
python -m uvicorn server_v2:app --reload --port 8000

# Terminal 3: UI (NEW VERSION)
cd ui
streamlit run ui_v2.py
```

---

## 📝 API Reference

### **Chat Endpoint**
```http
POST /chat
{
  "message": "Transfer 6000 to Kiran",
  "session_id": "optional-session-id",
  "user_id": "default_user"
}
```

### **Workflow Approval**
```http
POST /workflow/{session_id}/approve
{
  "approver_id": "manager@bank.com",
  "approved": true,
  "reason": "Approved for valid business reason"
}
```

### **Workflow Status**
```http
GET /workflow/{session_id}/status
```

### **Session List**
```http
GET /sessions?user_id=default_user
```

---

## 🎓 Summary

This example demonstrates a **production-grade workflow engine** with:

- ✅ **7 automatic checkpoints** saved
- ✅ **Human-in-the-Loop** approval at $5000 threshold
- ✅ **Session management** with full history
- ✅ **Resume capability** from any checkpoint
- ✅ **Complete audit trail** in database
- ✅ **Idempotent execution** support
- ✅ **Real-time UI updates** for approvals

The system is **ready for production** with proper error handling, state persistence, and scalability features!
