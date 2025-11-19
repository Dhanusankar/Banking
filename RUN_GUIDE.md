# 🚀 Banking AI POC - System Walkthrough

## How to Run and Understand the Complete System

### Prerequisites
- ✅ Java 17+ installed
- ✅ Python 3.11+ installed
- ✅ Maven installed
- ✅ All dependencies installed

---

## Step 1: Start the Backend (Java Spring Boot)

**Terminal 1:**
```powershell
cd C:\Users\dhanu\bank_ai\banking-ai-poc\backend-java\banking-backend
mvn spring-boot:run
```

**What happens:**
- Java Spring Boot application starts
- Listens on **http://localhost:8081**
- Exposes REST API endpoints:
  - `GET /api/balance?accountId=123` - Get account balance
  - `POST /api/transfer` - Execute money transfer
  - `GET /api/statement?accountId=123` - Get account statement
  - `GET /api/loan?accountId=123` - Get loan information
- Uses in-memory data (resets on restart)

**Wait for:** `Started BankingApplication in X seconds`

**Test it:**
```powershell
curl http://localhost:8081/api/balance?accountId=123
```

Expected response:
```json
{
  "accountId": "123",
  "balance": 50000.0,
  "currency": "USD"
}
```

---

## Step 2: Start the AI Orchestrator (Python + LangGraph)

**Terminal 2:**
```powershell
cd C:\Users\dhanu\bank_ai\banking-ai-poc\ai-orchestrator
uvicorn server:app --reload --port 8000
```

**What happens:**
- FastAPI application starts
- Listens on **http://localhost:8000**
- Loads LangGraph workflow with nodes:
  - Validation node
  - Balance inquiry node
  - Money transfer node (with HIL logic)
  - Account statement node
  - Loan inquiry node
  - Fallback node
- Connects to SQLite database (`workflows.db`)
- Ready to process natural language queries

**Wait for:** `Uvicorn running on http://127.0.0.1:8000`

**Test it:**
```powershell
# View API documentation
Start http://localhost:8000/docs

# Or test with curl
curl -X POST http://localhost:8000/chat `
  -H "Content-Type: application/json" `
  -d '{"message":"What is my balance?"}'
```

---

## Step 3: Start the Streamlit UI

**Terminal 3:**
```powershell
cd C:\Users\dhanu\bank_ai\banking-ai-poc\ui
streamlit run ui.py
```

**What happens:**
- Streamlit web app starts
- Listens on **http://localhost:8501**
- Opens automatically in your browser
- Provides chat interface
- Connects to orchestrator at `http://localhost:8000/chat`

**Wait for:** Browser opens to `http://localhost:8501`

---

## Step 4: Understanding the Workflow

### 🔹 Scenario 1: Low-Value Transfer (Auto-Approved)

**In Streamlit UI, type:**
```
Transfer 1000 to Kiran
```

**What happens behind the scenes:**

1. **UI → Orchestrator:**
   ```json
   POST /chat
   {
     "message": "Transfer 1000 to Kiran",
     "user_id": "default_user"
   }
   ```

2. **Orchestrator - Intent Classification:**
   ```python
   classify_intent("Transfer 1000 to Kiran")
   # Returns: "money_transfer"
   ```

3. **Orchestrator - LangGraph Workflow:**
   ```
   Entry Point: validate_input node
       ↓
   Route to: money_transfer node
       ↓
   Extract: amount=1000, recipient="kiran"
       ↓
   Check: 1000 < 5000 (threshold)
       ↓
   Decision: Auto-approve (low value)
       ↓
   Prepare API call to backend
   ```

4. **Orchestrator → Backend:**
   ```json
   POST http://localhost:8081/api/transfer
   {
     "fromAccount": "123",
     "toAccount": "kiran",
     "amount": 1000
   }
   ```

5. **Backend processes:**
   - Validates accounts
   - Checks balance
   - Executes transfer
   - Returns success

6. **Response chain:**
   ```
   Backend → Orchestrator → UI → User
   ```

**Result in UI:**
```json
{
  "intent": "money_transfer",
  "status_code": 200,
  "data": {
    "success": true,
    "message": "Transfer completed: $1000 to kiran"
  }
}
```

---

### 🔹 Scenario 2: High-Value Transfer (Requires Approval)

**In Streamlit UI, type:**
```
Transfer 10000 to Kiran
```

**What happens behind the scenes:**

1. **UI → Orchestrator:** (same as before)

2. **Orchestrator - LangGraph Workflow:**
   ```
   Entry Point: validate_input node
       ↓
   Route to: money_transfer node
       ↓
   Extract: amount=10000, recipient="kiran"
       ↓
   Check: 10000 >= 5000 (threshold)
       ↓
   Decision: REQUIRES APPROVAL ⚠️
       ↓
   Create session in database
       ↓
   Create approval request
       ↓
   Save state for later resumption
       ↓
   Return "pending_approval" status
   ```

3. **Database writes:**
   ```sql
   INSERT INTO workflow_sessions (session_id, user_id, status, ...)
   VALUES ('abc-123', 'default_user', 'pending_approval', ...)
   
   INSERT INTO pending_approvals (approval_id, amount, recipient, ...)
   VALUES ('xyz-789', 10000, 'kiran', ...)
   ```

4. **Response to UI:**
   ```json
   {
     "status": "pending_approval",
     "message": "Transfer of $10000 to kiran requires approval",
     "approval_id": "xyz-789",
     "session_id": "abc-123"
   }
   ```

**What the user sees:**
```
Transfer of $10000 to kiran requires approval. 
Approval ID: xyz-789
```

---

### 🔹 Scenario 3: Manager Approves Transfer

**Option A: Via API (Python script or curl):**
```powershell
curl -X POST http://localhost:8000/approve `
  -H "Content-Type: application/json" `
  -d '{
    "approval_id": "xyz-789",
    "approved": true,
    "approver_id": "manager@bank.com"
  }'
```

**What happens:**

1. **Orchestrator receives approval:**
   ```python
   /approve endpoint called
   ```

2. **Database lookup:**
   ```sql
   SELECT * FROM pending_approvals 
   WHERE approval_id = 'xyz-789' AND status = 'pending'
   ```

3. **Update approval status:**
   ```sql
   UPDATE pending_approvals 
   SET status = 'approved', 
       approver_id = 'manager@bank.com',
       approved_at = NOW()
   WHERE approval_id = 'xyz-789'
   ```

4. **Execute the transfer:**
   ```json
   POST http://localhost:8081/api/transfer
   {
     "fromAccount": "123",
     "toAccount": "kiran",
     "amount": 10000
   }
   ```

5. **Update session:**
   ```sql
   UPDATE workflow_sessions 
   SET status = 'approved' 
   WHERE session_id = 'abc-123'
   ```

6. **Response:**
   ```json
   {
     "status": "approved",
     "approval_id": "xyz-789",
     "transfer_result": {
       "success": true,
       "message": "Transfer completed"
     }
   }
   ```

---

### 🔹 Scenario 4: Other Banking Operations

**Balance Inquiry:**
```
User: "What's my balance?"
  ↓
Intent: balance_inquiry
  ↓
Node: balance_tool
  ↓
API: GET http://localhost:8081/api/balance?accountId=123
  ↓
Response: {"accountId": "123", "balance": 50000.0}
```

**Account Statement:**
```
User: "Show my account statement"
  ↓
Intent: account_statement
  ↓
Node: account_statement_tool
  ↓
API: GET http://localhost:8081/api/statement?accountId=123
  ↓
Response: Recent transactions list
```

**Loan Inquiry:**
```
User: "What loan options do I have?"
  ↓
Intent: loan_inquiry
  ↓
Node: loan_inquiry_tool
  ↓
API: GET http://localhost:8081/api/loan?accountId=123
  ↓
Response: Available loan products
```

---

## Step 5: Verify Database State

**Check pending approvals:**
```powershell
cd C:\Users\dhanu\bank_ai\banking-ai-poc\ai-orchestrator
python
```

```python
from persistence import persistence

# View pending approvals
approvals = persistence.get_pending_approvals()
for a in approvals:
    print(f"${a['amount']} to {a['recipient']} - {a['approval_id']}")

# View session status
status = persistence.get_session_status('abc-123')
print(status)
```

**Or query SQLite directly:**
```powershell
sqlite3 C:\Users\dhanu\bank_ai\banking-ai-poc\ai-orchestrator\workflows.db
```

```sql
-- View all sessions
SELECT * FROM workflow_sessions ORDER BY created_at DESC LIMIT 5;

-- View all approvals
SELECT * FROM pending_approvals ORDER BY requested_at DESC;

-- Count by status
SELECT status, COUNT(*) FROM pending_approvals GROUP BY status;
```

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│                    USER (Browser)                       │
│              http://localhost:8501                      │
└────────────────────┬────────────────────────────────────┘
                     │
                     │ HTTP POST /chat
                     │ {"message": "Transfer 10000 to Kiran"}
                     ▼
┌─────────────────────────────────────────────────────────┐
│            AI ORCHESTRATOR (FastAPI)                    │
│              http://localhost:8000                      │
│                                                         │
│  ┌──────────────────────────────────────────┐          │
│  │         LangGraph StateGraph             │          │
│  │                                          │          │
│  │  validate_input → transfer_tool          │          │
│  │                      │                   │          │
│  │         ┌────────────┴────────────┐      │          │
│  │         │                         │      │          │
│  │    < $5000                   ≥ $5000     │          │
│  │  Auto-Execute            Create Approval │          │
│  │         │                         │      │          │
│  │         ▼                         ▼      │          │
│  │   Backend API            SQLite DB       │          │
│  └──────────────────────────────────────────┘          │
│                     │                        │          │
│                     ├─► workflows.db ◄───────┘          │
│                     │                                   │
└─────────────────────┼───────────────────────────────────┘
                      │
                      │ HTTP POST /api/transfer
                      ▼
┌─────────────────────────────────────────────────────────┐
│         BACKEND (Java Spring Boot)                      │
│              http://localhost:8081                      │
│                                                         │
│  ┌─────────────────┐    ┌──────────────────┐          │
│  │  BankController │───►│   BankService    │          │
│  └─────────────────┘    └──────────────────┘          │
│                                │                        │
│                                ▼                        │
│                         In-Memory Data                  │
│                     (Account: 123, Balance: 50000)      │
└─────────────────────────────────────────────────────────┘
```

---

## Key Concepts

### 1. **LangGraph Workflow**
- **Graph-based orchestration** instead of linear if/else
- **State management** - maintains context through nodes
- **Extensible** - easy to add new nodes for new features

### 2. **Human-in-the-Loop (HIL)**
- **Threshold detection** - automatically identifies high-risk operations
- **Pause/Resume** - workflow pauses for approval, resumes after
- **Audit trail** - all decisions logged in database

### 3. **Persistence**
- **SQLite database** - stores workflow state and approvals
- **Session tracking** - maintains conversation history
- **Resumable** - can pick up where left off after restart

### 4. **Modular Architecture**
- **Backend** - business logic, data access
- **Orchestrator** - AI logic, workflow management
- **UI** - user interaction, presentation

---

## Testing Checklist

Run through this checklist to verify everything works:

- [ ] Backend starts on port 8081
- [ ] Orchestrator starts on port 8000
- [ ] UI starts on port 8501 and opens in browser
- [ ] Balance inquiry works
- [ ] Low-value transfer (< $5000) executes immediately
- [ ] High-value transfer (≥ $5000) creates approval request
- [ ] Pending approvals can be listed via API
- [ ] Approval execution works and transfers money
- [ ] Database persists state across requests
- [ ] All workflows complete successfully

---

## Troubleshooting

**Backend won't start:**
- Check Java version: `java -version` (need 17+)
- Check port 8081 is free: `netstat -an | findstr 8081`
- Run from correct directory: `backend-java/banking-backend`

**Orchestrator errors:**
- Check Python version: `python --version` (need 3.11+)
- Install dependencies: `pip install -r requirements.txt`
- Check LangGraph installed: `python -c "import langgraph; print('OK')"`

**UI can't connect:**
- Verify orchestrator is running: `curl http://localhost:8000/docs`
- Check ORCHESTRATOR_URL in ui.py matches orchestrator address

**Database issues:**
- Delete and recreate: `del workflows.db` then restart orchestrator
- Check file permissions on workflows.db

---

## Next Steps

1. **Try all sample prompts** in the UI
2. **Monitor the terminals** to see debug output
3. **Check the database** to see state persistence
4. **Read the code** to understand implementation
5. **Extend the system** with new features

**Documentation:**
- README.md - General overview
- DEPLOYMENT.md - Deployment guides
- HIL_GUIDE.md - Approval system details
- WORKFLOW_VERIFICATION.md - Test results

**Repository:** https://github.com/Dhanusankar/Banking
