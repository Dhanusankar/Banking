# Banking AI POC - Complete System Architecture Guide

## 🎯 Executive Summary

This document provides a complete reverse-engineered understanding of the Banking AI POC system - a production-grade conversational AI workflow engine built with LangGraph, FastAPI, and Spring Boot.

**What Does This System Do?**
- Allows users to chat naturally to perform banking operations
- Automatically classifies user intent (balance check, transfer, statement, loan)
- Routes requests through an intelligent workflow graph
- Pauses high-value transfers ($5000+) for human approval
- Saves checkpoints at every step for fault tolerance
- Manages sessions across multiple conversations
- Resumes workflows after approval/rejection

---

## 📊 System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         USER INTERFACE LAYER                        │
│                    (Streamlit - ui_v2.py)                          │
│  - Chat interface with conversation history                        │
│  - Real-time approval panel for pending transfers                  │
│  - Session tracking sidebar (status, checkpoints, executions)      │
└─────────────────┬───────────────────────────────────────────────────┘
                  │ HTTP REST API
                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      AI ORCHESTRATOR LAYER                          │
│                    (FastAPI - server_v2.py)                        │
│                                                                     │
│  Endpoints:                                                         │
│  ✓ POST /chat                    - Process user messages           │
│  ✓ POST /workflow/{id}/approve   - Approve pending transfers       │
│  ✓ GET  /workflow/{id}/status    - Get session details            │
│  ✓ GET  /approvals/pending       - List pending approvals         │
│  ✓ GET  /sessions                - List all sessions              │
│  ✓ GET  /health                  - Health check                   │
└─────────────────┬───────────────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     WORKFLOW ENGINE LAYER                           │
│                  (LangGraph - banking_graph.py)                    │
│                                                                     │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐   │
│  │ Validate │───▶│ Classify │───▶│  Route   │───▶│ Execute  │   │
│  │  Input   │    │  Intent  │    │  Intent  │    │  Action  │   │
│  └──────────┘    └──────────┘    └──────────┘    └──────────┘   │
│                                                                     │
│  Intent Routes:                                                     │
│  • balance_inquiry    → balance_inquiry_node                       │
│  • money_transfer     → prepare → HIL → execute                    │
│  • account_statement  → account_statement_node                     │
│  • loan_inquiry       → loan_inquiry_node                          │
│  • fallback           → fallback_node                              │
└─────────────────┬───────────────────────────────────────────────────┘
                  │
                  ├─────────────────────────────────────────┐
                  ▼                                         ▼
┌─────────────────────────────────────┐  ┌──────────────────────────────┐
│      SUPPORT COMPONENTS             │  │    BACKEND SERVICES          │
│                                     │  │                              │
│  1. checkpoint_store.py            │  │  Java Spring Boot Backend   │
│     - State persistence            │  │  (Port 8081)                │
│     - SQLite/Redis backends        │  │                              │
│     - Save/load/clear checkpoints  │  │  Endpoints:                 │
│                                     │  │  ✓ GET  /api/balance        │
│  2. hil_node.py                    │  │  ✓ POST /api/transfer       │
│     - Human approval logic         │  │  ✓ GET  /api/statement      │
│     - Threshold checking ($5000)   │  │  ✓ GET  /api/loan           │
│     - Pause/resume workflows       │  │                              │
│                                     │  │  Data:                      │
│  3. session_manager.py             │  │  - In-memory accounts       │
│     - Session lifecycle            │  │  - Account 123: $50,000     │
│     - Conversation history         │  │  - Account kiran: $1,000    │
│     - Status tracking              │  │                              │
│                                     │  └──────────────────────────────┘
│  4. persistence.py                  │
│     - Approval tracking             │
│     - Workflow sessions DB          │
│     - Status management             │
│                                     │
│  5. intent_classifier.py            │
│     - Rule-based classification     │
│     - Keyword matching              │
│                                     │
│  6. transfer_extractor.py           │
│     - Regex-based extraction        │
│     - Amount & recipient parsing    │
└─────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                        STORAGE LAYER                                │
│                                                                     │
│  • checkpoints.db   - Workflow state snapshots (7 per transfer)    │
│  • workflows.db     - Session metadata and status                  │
│  • pending_approvals - High-value transfer requests                │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 🔍 Component Deep Dive

### 1. **Backend Java Service** (`backend-java/banking-backend/`)

**Purpose:** Core banking operations API

**Technology Stack:**
- Spring Boot 3.1.4
- Java 17
- Maven build system
- In-memory data store (ConcurrentHashMap)

**Key Files:**
```
BankingApplication.java    - Main entry point
BankController.java        - REST endpoints
BankService.java           - Business logic
Account.java               - Account model
```

**Data Model:**
```java
Account {
    accountId: String
    balance: Double
}

// Pre-seeded accounts:
"123"   → $50,000  (primary account)
"kiran" → $1,000   (recipient account)
```

**API Endpoints:**
| Endpoint | Method | Purpose | Input | Output |
|----------|--------|---------|-------|--------|
| `/api/balance` | GET | Check account balance | `?accountId=123` | `{accountId, balance}` |
| `/api/transfer` | POST | Execute transfer | `{fromAccount, toAccount, amount}` | `{success, message}` |
| `/api/statement` | GET | Get account statement | `?accountId=123` | Plain text statement |
| `/api/loan` | GET | Loan eligibility | `?accountId=123` | Plain text loan info |

**Business Logic:**
```java
// Transfer validation
1. Check source account exists
2. Check destination account exists
3. Validate amount > 0
4. Check sufficient balance
5. Deduct from source
6. Add to destination
7. Return success/failure
```

---

### 2. **Intent Classifier** (`intent_classifier.py`)

**Purpose:** Classify user's natural language into actionable intents

**Algorithm:** Rule-based keyword matching

**Intent Categories:**
```python
balance_inquiry     → "balance", "what's my balance"
money_transfer      → "transfer", "send", "pay"
account_statement   → "statement", "show statement"
loan_inquiry        → "loan", "apply for loan"
fallback           → Anything else
```

**Examples:**
```
User: "What's my balance?"           → balance_inquiry
User: "Transfer 1000 to Kiran"       → money_transfer
User: "Show me my statement"         → account_statement
User: "Can I get a loan?"            → loan_inquiry
User: "Hello there"                  → fallback
```

---

### 3. **Transfer Extractor** (`transfer_extractor.py`)

**Purpose:** Extract structured data from natural language transfer requests

**Technology:** Regex pattern matching

**Patterns:**
```python
AMOUNT_RE    = r"(\d+(?:[\.,]\d{1,2})?)"
  Example: "transfer 1000" → 1000
           "send 1,500.50" → 1500.50

RECIPIENT_RE = r"to\s+(account\s*\d+|\w+)"
  Example: "to kiran"      → "kiran"
           "to account 456" → "456"

POSSESSIVE_RE = r"(\w+)'s\s+account"
  Example: "to John's account" → "John"
```

**Extraction Flow:**
```
Input: "Transfer 6000 to Kiran's account"
  ↓
1. Extract amount:   6000
2. Extract recipient: Kiran
3. Default account:  123 (from user's account)
  ↓
Output: {
  amount: 6000.0,
  recipient: "kiran",
  from_account: "123"
}
```

---

### 4. **Checkpoint Store** (`checkpoint_store.py`)

**Purpose:** Production-grade state persistence with dual backend support

**Architecture:**
```
CheckpointStore (High-level API)
    │
    ├─── SQLiteCheckpointBackend (Development)
    │    - File: checkpoints.db
    │    - Fast local storage
    │
    └─── RedisCheckpointBackend (Production)
         - Distributed cache
         - High availability
```

**Database Schema (SQLite):**
```sql
CREATE TABLE checkpoints (
    id INTEGER PRIMARY KEY,
    session_id TEXT NOT NULL,           -- Links to workflow session
    checkpoint_id TEXT UNIQUE NOT NULL, -- Unique checkpoint identifier
    node_id TEXT,                       -- Graph node that created it
    state TEXT NOT NULL,                -- JSON serialized state
    metadata TEXT,                      -- Additional context
    created_at TEXT NOT NULL            -- ISO timestamp
);

CREATE INDEX idx_session ON checkpoints(session_id);
CREATE INDEX idx_checkpoint ON checkpoints(checkpoint_id);
```

**Key Operations:**
```python
# Save checkpoint
checkpoint_store.save_checkpoint(
    session_id="abc-123",
    node_id="transfer_execute",
    state={...},
    metadata={"user_id": "user@bank.com"}
)

# Load latest checkpoint
checkpoint = checkpoint_store.load_checkpoint("abc-123")

# List all checkpoints
checkpoints = checkpoint_store.list_checkpoints("abc-123")

# Clear session
checkpoint_store.clear_checkpoints("abc-123")
```

**Checkpoint Data Structure:**
```json
{
  "checkpoint_id": "uuid-v4",
  "node_id": "money_transfer_execute",
  "state": {
    "message": "Transfer 6000 to Kiran",
    "intent": "money_transfer",
    "amount": 6000.0,
    "recipient": "kiran",
    "execution_history": [...]
  },
  "metadata": {
    "user_id": "default_user",
    "node": "money_transfer_execute",
    "phase": "end"
  },
  "created_at": "2025-11-20T10:30:45.123456"
}
```

---

### 5. **Human-in-the-Loop Node** (`hil_node.py`)

**Purpose:** Reusable workflow pause mechanism for human approvals

**Status States:**
```python
PENDING   → Waiting for human decision
APPROVED  → Human approved, resume workflow
REJECTED  → Human rejected, cancel workflow
TIMEOUT   → Approval request expired
```

**Architecture:**
```python
HILNode(
    node_id="transfer_approval",
    approval_message="High-value transfer needs approval",
    approval_threshold=lambda state: state['amount'] >= 5000,
    auto_approve=False,
    timeout_seconds=3600
)
```

**Execution Flow:**
```
┌─────────────────────────┐
│ HILNode.execute(state)  │
└────────────┬────────────┘
             │
             ▼
    ┌────────────────────┐
    │ Check threshold    │  amount >= $5000?
    └────────┬───────────┘
             │
        ┌────┴────┐
        │         │
       YES       NO
        │         │
        ▼         ▼
  ┌──────────┐  ┌──────────┐
  │  PAUSE   │  │ CONTINUE │
  │ Workflow │  │ Workflow │
  └────┬─────┘  └──────────┘
       │
       ▼
  Save checkpoint
  Create approval request
  Return PENDING_APPROVAL
       │
       │ (Wait for human)
       │
       ▼
  approve(session_id, approver_id)
       │
       ▼
  Load checkpoint
  Update state
  Mark as APPROVED
       │
       ▼
  resume_workflow(session_id)
```

**Threshold Function Examples:**
```python
# Amount-based threshold
lambda state: state['amount'] >= 5000

# Multiple conditions
lambda state: (
    state['amount'] >= 5000 or 
    state['recipient'] == 'international'
)

# Time-based (working hours only)
lambda state: not is_working_hours()

# Always require approval
lambda state: True
```

**Database Integration:**
```sql
-- HIL creates approval request
INSERT INTO pending_approvals (
    approval_id,
    session_id,
    workflow_type,
    request_data,
    status,
    amount,
    recipient,
    requested_at
) VALUES (...);
```

---

### 6. **Session Manager** (`session_manager.py`)

**Purpose:** Manage workflow execution sessions and conversation history

**Session Lifecycle:**
```
CREATE → ACTIVE → PENDING_APPROVAL → APPROVED/REJECTED → COMPLETED
   │        │            │                  │                │
   │        │            │                  │                └─→ Final
   │        │            │                  └─→ Resume execution
   │        │            └─→ Pause for HIL
   │        └─→ Normal execution
   └─→ Initialize session
```

**Session Status Enum:**
```python
ACTIVE            - Workflow executing normally
PENDING_APPROVAL  - Paused for HIL approval
APPROVED          - Approval granted, resuming
REJECTED          - Approval denied, cancelled
COMPLETED         - Workflow finished successfully
FAILED            - Workflow encountered error
TIMEOUT           - Approval timeout expired
```

**WorkflowSession Class:**
```python
class WorkflowSession:
    session_id: str           # UUID for this session
    user_id: str              # User who initiated
    workflow_type: str        # "banking", "loans", etc.
    status: SessionStatus     # Current status
    conversation_history: List[ConversationMessage]
    workflow_state: Dict      # Current state snapshot
    metadata: Dict            # created_at, last_activity
    current_node: str         # Last executed node
    execution_count: int      # For idempotency tracking
```

**Conversation Message:**
```python
{
  "role": "user",  # or "assistant" or "system"
  "content": "Transfer 6000 to Kiran",
  "metadata": {},
  "timestamp": "2025-11-20T10:30:00"
}
```

**Key Operations:**
```python
# Create session
session = session_manager.create_session(
    user_id="user@bank.com",
    workflow_type="banking"
)

# Add conversation message
session.add_message("user", "What's my balance?")
session.add_message("assistant", "Your balance is $50,000")

# Update state
session.update_state(
    {"intent": "balance_inquiry", "amount": 50000},
    node_id="balance_inquiry"
)

# Check idempotency
if session.is_idempotent_execution():
    # This is a retry/duplicate request
    pass

# Save session
session_manager.save_session(session)

# Get or create
session = session_manager.get_or_create_session(
    session_id="abc-123",  # None = create new
    user_id="user@bank.com"
)
```

**Idempotency Tracking:**
```
Request 1: execution_count = 0 → Process normally
Request 2: execution_count = 1 → Detected as duplicate
Request 3: execution_count = 2 → Detected as duplicate
```

---

### 7. **Persistence Layer** (`persistence.py`)

**Purpose:** Database operations for workflow state and approvals

**Database Schema:**
```sql
-- Workflow sessions
CREATE TABLE workflow_sessions (
    session_id TEXT PRIMARY KEY,
    user_id TEXT,
    workflow_type TEXT,
    state TEXT,              -- JSON serialized
    status TEXT,             -- 'active', 'pending', etc.
    created_at TEXT,
    updated_at TEXT
);

-- Pending approvals
CREATE TABLE pending_approvals (
    approval_id TEXT PRIMARY KEY,
    session_id TEXT,
    workflow_type TEXT,
    request_data TEXT,       -- JSON serialized
    status TEXT,             -- 'pending', 'approved', 'rejected'
    amount REAL,
    recipient TEXT,
    requested_at TEXT,
    approved_at TEXT,
    approver_id TEXT,
    rejection_reason TEXT,
    FOREIGN KEY (session_id) REFERENCES workflow_sessions(session_id)
);
```

**CRUD Operations:**
```python
# Create session
session_id = persistence.create_session(
    user_id="user@bank.com",
    workflow_type="banking"
)

# Save state
persistence.save_state(
    session_id=session_id,
    state={"intent": "transfer", "amount": 6000},
    status="pending_approval"
)

# Load state
state = persistence.load_state(session_id)

# Create approval request
approval_id = persistence.create_approval_request(
    session_id=session_id,
    workflow_type="banking",
    request_data={"amount": 6000, "recipient": "kiran"},
    amount=6000,
    recipient="kiran"
)

# Approve request
result = persistence.approve_request(
    approval_id=approval_id,
    approver_id="manager@bank.com"
)

# Reject request
result = persistence.reject_request(
    approval_id=approval_id,
    reason="Insufficient documentation",
    approver_id="manager@bank.com"
)

# Get pending approvals
approvals = persistence.get_pending_approvals()
# Returns: [
#   {
#     "approval_id": "...",
#     "session_id": "...",
#     "amount": 6000,
#     "recipient": "kiran",
#     "requested_at": "..."
#   }
# ]

# Get session status
status = persistence.get_session_status(session_id)
```

---

### 8. **Banking Graph** (`banking_graph.py`)

**Purpose:** LangGraph workflow orchestrating the entire banking flow

**State Schema:**
```python
class BankingState(TypedDict):
    message: str                # User input
    intent: str                 # Classified intent
    user_id: str                # User identifier
    session_id: str             # Session UUID
    amount: float               # Transfer amount
    recipient: str              # Transfer recipient
    from_account: str           # Source account (default: "123")
    request_data: dict          # Backend API request
    response: dict              # API response
    error: str                  # Error message if any
    hil_decision: dict          # Approval decision
    execution_history: List     # Node execution trace
```

**Workflow Graph:**
```
                    START
                      │
                      ▼
              ┌───────────────┐
              │   validate    │  Validate input & classify intent
              └───────┬───────┘
                      │
                      ▼
              ┌───────────────┐
              │ route_intent  │  Route based on intent
              └───────┬───────┘
                      │
      ┌───────────────┼───────────────┬───────────────┐
      │               │               │               │
      ▼               ▼               ▼               ▼
┌──────────┐  ┌──────────────┐  ┌──────────┐  ┌──────────┐
│ balance  │  │   transfer   │  │statement │  │  loan    │
│ inquiry  │  │ (multi-step) │  │          │  │ inquiry  │
└────┬─────┘  └──────┬───────┘  └────┬─────┘  └────┬─────┘
     │               │               │             │
     │        ┌──────┴──────┐        │             │
     │        ▼             ▼        │             │
     │   ┌─────────┐  ┌─────────┐   │             │
     │   │ prepare │  │   HIL   │   │             │
     │   └────┬────┘  └────┬────┘   │             │
     │        │            │        │             │
     │        │    ┌───────┴────┐   │             │
     │        │    │            │   │             │
     │        │    ▼            ▼   │             │
     │        │ APPROVED    REJECTED│             │
     │        │    │                │             │
     │        │    ▼                │             │
     │        │ ┌─────────┐         │             │
     │        │ │ execute │         │             │
     │        │ └────┬────┘         │             │
     │        │      │              │             │
     └────────┴──────┴──────────────┴─────────────┘
                      │
                      ▼
                    END
```

**Checkpoint Wrapper Decorator:**
```python
@checkpoint_wrapper("node_name")
def node_function(state: BankingState) -> BankingState:
    # Automatically saves checkpoint before & after execution
    # Adds to execution_history
    # Returns updated state
    pass
```

**Node Breakdown:**

#### 1. **Validate Input Node**
```python
@checkpoint_wrapper("validate_input")
def validate_input_node(state: BankingState) -> BankingState:
    """
    Checkpoint: intent_classified
    
    Steps:
    1. Check message is not empty
    2. Classify intent using intent_classifier
    3. Update state with intent
    """
    message = state.get("message", "")
    if not message:
        state["error"] = "Empty message"
        state["intent"] = "fallback"
        return state
    
    intent = classify_intent(message)
    state["intent"] = intent
    return state
```

#### 2. **Balance Inquiry Node**
```python
@checkpoint_wrapper("balance_inquiry")
def balance_inquiry_node(state: BankingState) -> BankingState:
    """
    Checkpoint: balance_checked
    
    Steps:
    1. Extract account ID from state
    2. Call GET /api/balance
    3. Store response in state
    """
    account_id = state.get("from_account", "123")
    response = requests.get(
        f"http://localhost:8081/api/balance",
        params={"accountId": account_id}
    )
    state["response"] = response.json()
    return state
```

#### 3. **Money Transfer Prepare Node**
```python
@checkpoint_wrapper("money_transfer_prepare")
def money_transfer_prepare_node(state: BankingState) -> BankingState:
    """
    Checkpoint: transfer_prepared
    
    Steps:
    1. Extract transfer details (amount, recipient)
    2. Validate details
    3. Prepare request_data for backend
    """
    details = extract_transfer_details(state["message"])
    
    state["amount"] = details["amount"]
    state["recipient"] = details["recipient"]
    state["request_data"] = {
        "fromAccount": "123",
        "toAccount": details["recipient"],
        "amount": details["amount"]
    }
    return state
```

#### 4. **Money Transfer HIL Node**
```python
def money_transfer_hil_node(state: BankingState) -> BankingState:
    """
    Checkpoint: hil_pending (if approval needed)
    Checkpoint: hil_approved (after approval)
    
    Steps:
    1. Check if amount >= $5000
    2. If YES: Pause workflow, save checkpoint, return PENDING_APPROVAL
    3. If NO: Continue automatically, set auto-approved flag
    """
    hil_result = transfer_hil_node.execute(state, session_id, user_id)
    
    if hil_result["status"] == "PENDING_APPROVAL":
        # Workflow PAUSES here
        state["response"] = hil_result
        state["_halt"] = True
        return state
    
    # Auto-approved
    state["hil_decision"] = {"approved": True, "auto": True}
    return state
```

#### 5. **Money Transfer Execute Node**
```python
@checkpoint_wrapper("money_transfer_execute")
def money_transfer_execute_node(state: BankingState) -> BankingState:
    """
    Checkpoint: transfer_executed
    
    Steps:
    1. Verify HIL approval
    2. Call POST /api/transfer
    3. Store result in state
    """
    if not state.get("hil_decision", {}).get("approved"):
        state["error"] = "Transfer not approved"
        return state
    
    response = requests.post(
        f"http://localhost:8081/api/transfer",
        json=state["request_data"]
    )
    state["response"] = response.json()
    return state
```

**Route Functions:**
```python
def route_after_validate(state: BankingState) -> str:
    """Route based on classified intent."""
    intent = state.get("intent")
    
    if intent == "balance_inquiry":
        return "balance_inquiry"
    elif intent == "money_transfer":
        return "money_transfer_prepare"
    elif intent == "account_statement":
        return "account_statement"
    elif intent == "loan_inquiry":
        return "loan_inquiry"
    else:
        return "fallback"
```

**Resume Workflow Function:**
```python
def resume_workflow(session_id: str, action: str) -> Dict:
    """
    Resume a paused workflow after HIL decision.
    
    Steps:
    1. Load checkpoint from checkpoint_store
    2. Load session from session_manager
    3. Update state with HIL decision
    4. Continue execution from money_transfer_execute
    5. Return final result
    """
    checkpoint = checkpoint_store.load_checkpoint(session_id)
    state = checkpoint["state"]
    
    # Update with approval
    state["hil_decision"] = {
        "approved": True,
        "approver_id": "...",
        "timestamp": "..."
    }
    
    # Continue execution
    result = money_transfer_execute_node(state)
    return result
```

---

### 9. **FastAPI Server** (`server_v2.py`)

**Purpose:** Production REST API for workflow management

**Endpoints:**

#### POST /chat
```python
Request:
{
  "message": "Transfer 6000 to Kiran",
  "session_id": "abc-123" (optional),
  "user_id": "user@bank.com"
}

Response (Normal):
{
  "reply": {
    "intent": "money_transfer",
    "status": "success",
    "data": {...}
  },
  "session_id": "abc-123",
  "execution_history": [...]
}

Response (Pending Approval):
{
  "reply": {
    "status": "PENDING_APPROVAL",
    "message": "High-value transfer needs approval",
    "approval_id": "xyz-789",
    "amount": 6000,
    "recipient": "kiran"
  },
  "session_id": "abc-123",
  "status": "PENDING_APPROVAL"
}
```

#### POST /workflow/{session_id}/approve
```python
Request:
{
  "approver_id": "manager@bank.com",
  "approved": true,
  "reason": "Verified with customer"
}

Response (Approved):
{
  "status": "approved",
  "session_id": "abc-123",
  "result": {
    "intent": "money_transfer",
    "status": "success",
    "data": {...}
  },
  "approved_by": "manager@bank.com"
}

Response (Rejected):
{
  "status": "rejected",
  "session_id": "abc-123",
  "reason": "Suspicious activity",
  "rejected_by": "manager@bank.com"
}
```

#### GET /workflow/{session_id}/status
```python
Response:
{
  "session_id": "abc-123",
  "user_id": "user@bank.com",
  "status": "PENDING_APPROVAL",
  "execution_count": 1,
  "checkpoints": 4,
  "current_node": "money_transfer_hil",
  "metadata": {
    "created_at": "2025-11-20T10:30:00",
    "last_activity": "2025-11-20T10:35:00"
  }
}
```

#### GET /approvals/pending
```python
Response:
{
  "pending_approvals": [
    {
      "approval_id": "xyz-789",
      "session_id": "abc-123",
      "workflow_type": "banking",
      "amount": 6000,
      "recipient": "kiran",
      "request_data": {...},
      "requested_at": "2025-11-20T10:35:00"
    }
  ]
}
```

#### GET /sessions
```python
Response:
{
  "sessions": [
    {
      "session_id": "abc-123",
      "user_id": "user@bank.com",
      "status": "PENDING_APPROVAL",
      "created_at": "..."
    }
  ]
}
```

---

### 10. **Streamlit UI** (`ui_v2.py`)

**Purpose:** Interactive web interface for users and approvers

**Layout:**
```
┌────────────────────────────────────────────────────────────────┐
│ 🏦 Banking AI — Production Workflow Engine                     │
├────────────────────────┬───────────────────────────────────────┤
│                        │                                       │
│  📊 SESSION INFO       │  💬 CHAT INTERFACE                    │
│  ─────────────────     │  ───────────────────                 │
│  Session: abc-123...   │  User: "Transfer 6000 to Kiran"      │
│  Status: PENDING       │  Bot:  "Transfer requires approval"  │
│  Executions: 1         │                                       │
│  Checkpoints: 4        │  [Input box: Type message...]         │
│                        │  [Send Button]                        │
│  ℹ️ FEATURES           │                                       │
│  ✅ Checkpointing      │                                       │
│  ✅ Human-in-Loop      │  ────────────────────────────────     │
│  ✅ Session Mgmt       │                                       │
│  ✅ Resume             │  🔔 PENDING APPROVALS                 │
│                        │  ───────────────────                 │
│  🔄 New Session        │  Transfer: $6000 → kiran              │
│                        │  Requested: 10:35 AM                  │
│                        │                                       │
│                        │  [✓ Approve] [✗ Reject]               │
│                        │                                       │
└────────────────────────┴───────────────────────────────────────┘
```

**Features:**

1. **Session Tracking Sidebar:**
   - Session ID display
   - Real-time status (ACTIVE, PENDING, COMPLETED)
   - Execution counter
   - Checkpoint counter
   - Execution details (user, node, timestamps)

2. **Chat Interface:**
   - Conversation history
   - Message timestamps
   - Error handling
   - Example prompts

3. **Dynamic Approval Panel:**
   - Appears only when approval needed
   - Shows transfer details
   - Approve/Reject buttons
   - Reason input for rejection
   - Real-time updates

4. **Workflow Status Display:**
   - Execution trace
   - Checkpoint timeline
   - Node progression

---

## 🔄 End-to-End Workflow Examples

### Example 1: Low-Value Transfer (Auto-Approved)

**User Input:** "Transfer 1000 to Kiran"

```
┌─────────────────────────────────────────────────────────────────┐
│ STEP 1: User sends message                                     │
└─────────────────────────────────────────────────────────────────┘
UI → POST /chat {message: "Transfer 1000 to Kiran"}

┌─────────────────────────────────────────────────────────────────┐
│ STEP 2: Server creates/gets session                            │
└─────────────────────────────────────────────────────────────────┘
session = session_manager.get_or_create_session()
session.add_message("user", "Transfer 1000 to Kiran")

┌─────────────────────────────────────────────────────────────────┐
│ STEP 3: Workflow execution starts                              │
└─────────────────────────────────────────────────────────────────┘
Node: validate_input
  ├─ Checkpoint: intent_classified [1/5]
  ├─ Classify: "money_transfer"
  └─ State: {intent: "money_transfer", message: "Transfer 1000..."}

Node: money_transfer_prepare
  ├─ Checkpoint: transfer_prepared [2/5]
  ├─ Extract: {amount: 1000, recipient: "kiran"}
  └─ State: {amount: 1000, recipient: "kiran", request_data: {...}}

Node: money_transfer_hil
  ├─ Check threshold: 1000 < 5000 ✓
  ├─ Result: BYPASSED (auto-approved)
  └─ State: {hil_decision: {approved: true, auto: true}}

Node: money_transfer_execute
  ├─ Checkpoint: transfer_executed [3/5]
  ├─ POST /api/transfer {fromAccount: "123", toAccount: "kiran", amount: 1000}
  ├─ Backend: Deduct $1000 from 123, Add $1000 to kiran
  ├─ Response: {success: true, message: "Transferred..."}
  └─ State: {response: {...}}

Node: END
  ├─ Checkpoint: response_sent [4/5]
  └─ Final state saved

┌─────────────────────────────────────────────────────────────────┐
│ STEP 4: Server responds                                        │
└─────────────────────────────────────────────────────────────────┘
Response: {
  reply: {
    intent: "money_transfer",
    status: "success",
    data: {success: true, message: "Transferred 1000.00 from 123 to kiran"}
  },
  session_id: "abc-123",
  execution_history: [...]
}

┌─────────────────────────────────────────────────────────────────┐
│ STEP 5: UI displays result                                     │
└─────────────────────────────────────────────────────────────────┘
Chat: Bot: "✓ Transferred $1,000.00 from 123 to kiran"
Sidebar: Checkpoints: 4, Status: COMPLETED
```

**Total Checkpoints:** 4
**Execution Time:** ~500ms
**Approval Required:** No

---

### Example 2: High-Value Transfer (Approval Required)

**User Input:** "Transfer 6000 to Kiran"

```
┌─────────────────────────────────────────────────────────────────┐
│ STEP 1-2: Same as Example 1 (User sends, session created)      │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ STEP 3: Workflow execution (First Phase)                       │
└─────────────────────────────────────────────────────────────────┘
Node: validate_input
  ├─ Checkpoint: intent_classified [1/7]
  └─ State: {intent: "money_transfer"}

Node: money_transfer_prepare
  ├─ Checkpoint: transfer_prepared [2/7]
  └─ State: {amount: 6000, recipient: "kiran"}

Node: money_transfer_hil
  ├─ Check threshold: 6000 >= 5000 ✗ (APPROVAL NEEDED)
  ├─ Checkpoint: hil_pending [3/7]
  ├─ Create approval request in DB
  ├─ Update session status → PENDING_APPROVAL
  ├─ PAUSE WORKFLOW ⏸️
  └─ State: {response: {status: "PENDING_APPROVAL", ...}, _halt: true}

┌─────────────────────────────────────────────────────────────────┐
│ STEP 4: Server responds with pending status                    │
└─────────────────────────────────────────────────────────────────┘
Response: {
  reply: {
    status: "PENDING_APPROVAL",
    message: "High-value transfer needs approval",
    approval_id: "xyz-789",
    amount: 6000,
    recipient: "kiran"
  },
  session_id: "abc-123",
  status: "PENDING_APPROVAL"
}

┌─────────────────────────────────────────────────────────────────┐
│ STEP 5: UI displays approval panel                             │
└─────────────────────────────────────────────────────────────────┘
Chat: Bot: "⏸️ Transfer requires manager approval"
Approval Panel: [Shows] $6000 → kiran
                [Buttons] Approve | Reject
Sidebar: Status: PENDING_APPROVAL, Checkpoints: 3

┌─────────────────────────────────────────────────────────────────┐
│ STEP 6: Manager approves (could be minutes/hours later)        │
└─────────────────────────────────────────────────────────────────┘
Manager clicks: [✓ Approve]
UI → POST /workflow/abc-123/approve {
  approver_id: "manager@bank.com",
  approved: true
}

┌─────────────────────────────────────────────────────────────────┐
│ STEP 7: Server processes approval                              │
└─────────────────────────────────────────────────────────────────┘
1. Load checkpoint [hil_pending]
2. Update approval in DB
3. Add HIL decision to state: {approved: true, approver_id: "manager@bank.com"}
4. Checkpoint: hil_approved [4/7]
5. RESUME WORKFLOW ▶️

┌─────────────────────────────────────────────────────────────────┐
│ STEP 8: Workflow execution (Second Phase - Resume)             │
└─────────────────────────────────────────────────────────────────┘
Node: money_transfer_execute
  ├─ Checkpoint: transfer_executed [5/7]
  ├─ Check: hil_decision.approved = true ✓
  ├─ POST /api/transfer {fromAccount: "123", toAccount: "kiran", amount: 6000}
  ├─ Backend: Deduct $6000 from 123, Add $6000 to kiran
  ├─ Response: {success: true, message: "Transferred..."}
  └─ State: {response: {...}}

Node: END
  ├─ Checkpoint: response_sent [6/7]
  └─ Final state saved

┌─────────────────────────────────────────────────────────────────┐
│ STEP 9: Server responds with success                           │
└─────────────────────────────────────────────────────────────────┘
Response: {
  status: "approved",
  session_id: "abc-123",
  result: {
    intent: "money_transfer",
    status: "success",
    data: {...}
  },
  approved_by: "manager@bank.com"
}

┌─────────────────────────────────────────────────────────────────┐
│ STEP 10: UI displays final result                              │
└─────────────────────────────────────────────────────────────────┘
Chat: Bot: "✓ Transfer approved by manager@bank.com"
      Bot: "✓ Transferred $6,000.00 from 123 to kiran"
Approval Panel: [Disappears]
Sidebar: Status: COMPLETED, Checkpoints: 7
```

**Total Checkpoints:** 7
**Execution Time:** ~500ms (split across 2 phases)
**Approval Required:** Yes
**Pause Duration:** Depends on manager (seconds to hours)

---

### Example 3: Balance Inquiry

**User Input:** "What's my balance?"

```
Node: validate_input
  ├─ Checkpoint: intent_classified [1/2]
  └─ Intent: balance_inquiry

Node: balance_inquiry
  ├─ Checkpoint: balance_checked [2/2]
  ├─ GET /api/balance?accountId=123
  ├─ Backend: Return {accountId: "123", balance: 50000}
  └─ Response: {intent: "balance_inquiry", status: "success", data: {...}}

Result: "Your balance is $50,000.00"
Checkpoints: 2
Time: ~200ms
```

---

## 🗄️ Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                      DATA PERSISTENCE FLOW                      │
└─────────────────────────────────────────────────────────────────┘

User Message
    │
    ▼
┌────────────────┐
│ Session Store  │ → workflows.db
│                │   - session_id
│                │   - user_id
│                │   - status
│                │   - conversation_history
└────────────────┘
    │
    ▼
Workflow Execution
    │
    ├──→ ┌────────────────┐
    │    │ Checkpoint DB  │ → checkpoints.db
    │    │                │   - checkpoint_id
    │    │                │   - session_id
    │    │                │   - node_id
    │    │                │   - state (JSON)
    │    │                │   - created_at
    │    └────────────────┘
    │
    └──→ ┌────────────────┐
         │ Approval Store │ → workflows.db (pending_approvals)
         │                │   - approval_id
         │                │   - session_id
         │                │   - amount
         │                │   - recipient
         │                │   - status
         └────────────────┘
             │
             ▼
         Manager Decision
             │
             ├─→ Approved  → Update approval status
             │               Resume workflow
             │               Execute transfer
             │
             └─→ Rejected  → Update approval status
                             Cancel workflow
                             Notify user
```

---

## 🔐 7 Checkpoints Explained

For a high-value transfer ($5000+), the system creates **7 checkpoints**:

| # | Checkpoint ID | Node | Purpose | State Captured |
|---|--------------|------|---------|----------------|
| 1 | `intent_classified` | validate_input | User intent identified | message, intent |
| 2 | `transfer_prepared` | money_transfer_prepare | Transfer details extracted | amount, recipient, request_data |
| 3 | `hil_pending` | money_transfer_hil | Workflow paused for approval | All state + approval_id |
| 4 | `hil_approved` | money_transfer_hil | Manager approved transfer | hil_decision with approver_id |
| 5 | `transfer_executed` | money_transfer_execute | Backend processed transfer | response with success/failure |
| 6 | `response_sent` | END | Final response prepared | Complete final state |
| 7 | `execution_complete` | (implicit) | Session marked complete | Session metadata updated |

**Why 7 checkpoints?**
- **Fault tolerance:** If system crashes at any point, can resume
- **Audit trail:** Complete history of workflow progression
- **Debugging:** Can inspect state at any step
- **Compliance:** Regulatory requirement for financial transactions

---

## 🚀 Startup Sequence

```bash
# Terminal 1: Backend (Java)
cd backend-java/banking-backend
mvn spring-boot:run
# Wait for: "Started BankingApplication in X seconds"
# Port: 8081

# Terminal 2: Orchestrator (Python)
cd ai-orchestrator
python -m uvicorn server_v2:app --reload --port 8000
# Wait for: "Uvicorn running on http://127.0.0.1:8000"
# Port: 8000

# Terminal 3: UI (Streamlit)
cd ui
streamlit run ui_v2.py
# Wait for: "You can now view your Streamlit app in your browser"
# Port: 8501 (opens automatically)
```

**Health Check:**
```bash
# Backend
curl http://localhost:8081/api/balance?accountId=123

# Orchestrator
curl http://localhost:8000/health

# UI
# Open browser: http://localhost:8501
```

---

## 📚 Key Design Patterns

### 1. **Decorator Pattern** (Checkpoint Wrapper)
```python
@checkpoint_wrapper("node_name")
def node_function(state):
    # Automatic checkpoint before & after
    pass
```

### 2. **Strategy Pattern** (Backend Selection)
```python
CheckpointBackend
  ├─ SQLiteCheckpointBackend  (Development)
  └─ RedisCheckpointBackend   (Production)
```

### 3. **State Machine** (Session Status)
```
ACTIVE → PENDING_APPROVAL → APPROVED → COMPLETED
                          → REJECTED
```

### 4. **Builder Pattern** (HIL Node)
```python
HILNodeBuilder.for_transfer()
    .with_threshold(5000)
    .with_timeout(3600)
    .build()
```

### 5. **Facade Pattern** (Session Manager)
```python
# Complex operations hidden behind simple interface
session_manager.get_or_create_session()
```

---

## 🎓 Learning Points

### What Makes This Production-Grade?

1. **State Persistence:**
   - Every step saved to database
   - System can crash and resume exactly where it left off
   - No data loss

2. **Human-in-the-Loop:**
   - Critical operations require human approval
   - Workflow pauses and waits indefinitely
   - Resume capability after approval

3. **Session Management:**
   - Each conversation tracked independently
   - Full conversation history maintained
   - Idempotent execution (duplicate requests handled)

4. **Observability:**
   - 7 checkpoints per workflow = complete audit trail
   - Execution history tracked
   - Status visible in real-time

5. **Error Handling:**
   - Graceful degradation
   - Clear error messages
   - State preserved even on failure

6. **Scalability:**
   - Backend can be swapped (SQLite → Redis)
   - Stateless API (can scale horizontally)
   - Session isolation (no cross-contamination)

---

## 🔧 Technology Stack Summary

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Backend API** | Java 17, Spring Boot 3.1.4 | Banking operations |
| **Orchestrator** | Python 3.11, FastAPI 0.104.1 | Workflow management |
| **Workflow Engine** | LangGraph 0.0.25 | State machine execution |
| **UI** | Streamlit 1.28.1 | Web interface |
| **Persistence** | SQLite 3 | Development database |
| **Cache (optional)** | Redis 7 | Production checkpoints |
| **Intent Classification** | Rule-based regex | NLU |
| **API Protocol** | REST (JSON) | Service communication |

---

## 📁 File Structure Summary

```
banking-ai-poc/
├── backend-java/
│   └── banking-backend/
│       ├── BankingApplication.java     [Entry point]
│       ├── BankController.java         [REST endpoints]
│       ├── BankService.java            [Business logic]
│       └── Account.java                [Data model]
│
├── ai-orchestrator/
│   ├── server_v2.py                    [FastAPI server]
│   ├── banking_graph.py                [LangGraph workflow]
│   ├── checkpoint_store.py             [State persistence]
│   ├── hil_node.py                     [Approval component]
│   ├── session_manager.py              [Session lifecycle]
│   ├── persistence.py                  [Database operations]
│   ├── intent_classifier.py            [Intent detection]
│   └── transfer_extractor.py           [Entity extraction]
│
├── ui/
│   ├── ui_v2.py                        [Streamlit interface]
│   └── requirements.txt                [Python dependencies]
│
└── *.db files
    ├── checkpoints.db                  [Checkpoint storage]
    └── workflows.db                    [Session/approval storage]
```

**Total Lines of Code:** ~3,600
**Core Components:** 10
**API Endpoints:** 10
**Database Tables:** 3
**Checkpoints per Transfer:** 7

---

## 🎯 Summary

This Banking AI POC is a **production-grade conversational workflow engine** that:

1. ✅ Classifies user intent from natural language
2. ✅ Routes requests through a LangGraph state machine
3. ✅ Saves 7 checkpoints per high-value transaction
4. ✅ Pauses for human approval on transfers ≥ $5000
5. ✅ Manages sessions with conversation history
6. ✅ Resumes workflows after approval/rejection
7. ✅ Provides real-time UI with approval notifications
8. ✅ Maintains complete audit trail
9. ✅ Handles errors gracefully with state preservation
10. ✅ Scales from development (SQLite) to production (Redis)

**Key Innovation:** The checkpoint + HIL system allows workflows to pause for hours/days, survive system crashes, and resume exactly where they stopped.

---

**Need More Details?** Check:
- `README_V2.md` - Complete v2 documentation
- `WORKFLOW_EXAMPLE.md` - Step-by-step trace with data
- `QUICKSTART_V2.md` - Quick start guide
