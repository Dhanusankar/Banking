# 🚀 Quick Start Guide - Banking AI v2.0

## What You Get

A **production-grade workflow engine** with:
- ✅ Automatic state checkpointing
- ✅ Human-in-the-loop approvals
- ✅ Session management
- ✅ Resume capability
- ✅ Complete audit trail

---

## 🏃 Run in 3 Steps

### **Step 1: Start Backend**
```powershell
cd C:\Users\dhanu\bank_ai\banking-ai-poc\backend-java\banking-backend
mvn spring-boot:run
```
✅ Wait for: `Started BankingApplication`

### **Step 2: Start Orchestrator v2**
```powershell
cd C:\Users\dhanu\bank_ai\banking-ai-poc\ai-orchestrator
python -m uvicorn server_v2:app --reload --port 8000
```
✅ Wait for: `Uvicorn running on http://127.0.0.1:8000`

### **Step 3: Start UI v2**
```powershell
cd C:\Users\dhanu\bank_ai\banking-ai-poc\ui
streamlit run ui_v2.py
```
✅ Browser opens to: `http://localhost:8501`

---

## 🧪 Test the Upgrade

### **Test 1: Low-Value Transfer (Auto-Approved)**
In the UI, type:
```
Transfer 2000 to Kiran
```

**Expected:**
- ✅ Executes immediately (< 1 second)
- ✅ No approval needed
- ✅ Session ID shown in sidebar
- ✅ Checkpoint counter increments

---

### **Test 2: High-Value Transfer (Requires Approval)**
In the UI, type:
```
Transfer 6000 to Kiran
```

**Expected:**
1. ⏳ Message: "Transfer requires approval"
2. 📋 Approval panel appears on right
3. 💰 Shows: $6,000 → kiran
4. ✅ Click "Approve" button
5. ✅ Transfer executes
6. 📊 Session status updates to "approved"

---

## 🎯 Key Features to Notice

### **1. Session Tracking (Sidebar)**
- Session ID displayed
- Status indicator (ACTIVE/PENDING_APPROVAL/COMPLETED)
- Execution count
- Checkpoint counter

### **2. Approval Panel (Right Side)**
- Only appears when needed
- Shows pending transfers
- One-click approve/reject
- Auto-refreshes after action

### **3. Conversation History**
- All messages preserved
- Timestamps shown
- Execution trace available (expand messages)

### **4. Checkpoints**
Watch the checkpoint counter increment:
- Validate input: +1
- Prepare transfer: +1
- HIL check: +1
- Execute transfer: +1
- **Total: 7 checkpoints per high-value transfer**

---

## 📊 Compare with v1

### **Run Both Versions Side-by-Side:**

**Terminal 1 (Backend):**
```powershell
cd backend-java/banking-backend
mvn spring-boot:run
```

**Terminal 2 (v1 Orchestrator on port 8000):**
```powershell
cd ai-orchestrator
uvicorn server:app --reload --port 8000
```

**Terminal 3 (v2 Orchestrator on port 8001):**
```powershell
cd ai-orchestrator
uvicorn server_v2:app --reload --port 8001
```

**Terminal 4 (v1 UI on port 8501):**
```powershell
cd ui
streamlit run ui.py --server.port 8501
```

**Terminal 5 (v2 UI on port 8502):**
```powershell
cd ui
streamlit run ui_v2.py --server.port 8502
```

**Access:**
- v1: http://localhost:8501
- v2: http://localhost:8502

---

## 🔍 API Testing

### **Chat Endpoint:**
```powershell
curl -X POST http://localhost:8000/chat `
  -H "Content-Type: application/json" `
  -d '{
    "message": "Transfer 6000 to Kiran",
    "user_id": "test_user"
  }'
```

### **Workflow Status:**
```powershell
# Replace SESSION_ID with actual session ID from chat response
curl http://localhost:8000/workflow/SESSION_ID/status
```

### **Approve Workflow:**
```powershell
curl -X POST http://localhost:8000/workflow/SESSION_ID/approve `
  -H "Content-Type: application/json" `
  -d '{
    "approver_id": "manager@test.com",
    "approved": true
  }'
```

### **List Sessions:**
```powershell
curl http://localhost:8000/sessions
```

### **Health Check:**
```powershell
curl http://localhost:8000/health
```

---

## 📂 File Structure

```
banking-ai-poc/
│
├── ai-orchestrator/
│   ├── agent.py                  # v1 agent (still works)
│   ├── server.py                 # v1 server
│   ├── banking_graph.py          # ✨ v2 LangGraph with checkpointing
│   ├── checkpoint_store.py       # ✨ v2 state persistence
│   ├── hil_node.py              # ✨ v2 HIL component
│   ├── session_manager.py        # ✨ v2 session management
│   ├── server_v2.py             # ✨ v2 production server
│   ├── requirements.txt          # v1 dependencies
│   └── requirements_v2.txt       # ✨ v2 dependencies
│
├── ui/
│   ├── ui.py                     # v1 UI
│   └── ui_v2.py                 # ✨ v2 enhanced UI
│
├── backend-java/                 # Unchanged (works with both)
│
├── README.md                     # Original README
├── README_V2.md                 # ✨ v2 comprehensive docs
└── WORKFLOW_EXAMPLE.md          # ✨ Step-by-step example
```

---

## 🐛 Troubleshooting

### **"Module not found" errors:**
```powershell
cd ai-orchestrator
pip install -r requirements_v2.txt
```

### **Port already in use:**
```powershell
# Check what's using port 8000
netstat -ano | findstr :8000

# Kill the process (replace PID)
taskkill /F /PID <PID>
```

### **Backend not responding:**
```powershell
# Test backend directly
curl http://localhost:8081/api/balance?accountId=123
```

### **Database locked error:**
```powershell
# Delete databases and restart
cd ai-orchestrator
del workflows.db checkpoints.db
```

---

## 📚 Learn More

- **README_V2.md** - Complete v2 documentation
- **WORKFLOW_EXAMPLE.md** - Step-by-step trace with "Transfer 6000 to Kiran"
- **RUN_GUIDE.md** - Original detailed guide
- **DEPLOYMENT.md** - Production deployment options

---

## 🎓 Key Concepts

### **1. Checkpointing**
Every node execution saves state. If system crashes, resume from last checkpoint.

### **2. Human-in-the-Loop (HIL)**
Workflow pauses at critical points (e.g., high-value transfers) for human approval.

### **3. Session Management**
Each conversation gets unique session ID. All state/history preserved per session.

### **4. Resume Logic**
After approval, workflow continues from exact point where it paused.

---

## ✅ Success Criteria

You've successfully set up v2 if:

- [x] Backend running on port 8081
- [x] Orchestrator v2 running on port 8000
- [x] UI v2 running on port 8501
- [x] Session ID displayed in sidebar
- [x] Low-value transfer executes immediately
- [x] High-value transfer shows approval panel
- [x] Approve button executes transfer
- [x] Checkpoint counter increments
- [x] Session status updates correctly

---

## 🚀 Next Steps

1. **Read WORKFLOW_EXAMPLE.md** - Understand complete flow
2. **Test all operations** - balance, transfer, statement, loan
3. **Try API endpoints** - Use curl to test workflow APIs
4. **Explore checkpoints** - Check databases to see saved state
5. **Customize thresholds** - Modify HIL approval amounts

---

## 🎉 You're Ready!

Your banking POC is now a **production-grade workflow engine**!

Features demonstrated:
- ✅ State persistence
- ✅ Automatic checkpointing
- ✅ Human-in-the-loop
- ✅ Session management
- ✅ Resume capability
- ✅ Complete observability

**Perfect for showcasing to stakeholders!** 🎯
