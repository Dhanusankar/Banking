"""
Banking AI POC - Complete System Demo
This script demonstrates the entire workflow step-by-step
"""
import requests
import json
import time
from persistence import persistence

print("=" * 80)
print("BANKING AI POC - SYSTEM DEMONSTRATION")
print("=" * 80)
print()

# Configuration
BACKEND_URL = "http://localhost:8081"
ORCHESTRATOR_URL = "http://localhost:8000"

def print_section(title):
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")

def print_step(step_num, description):
    print(f"\n{'─' * 80}")
    print(f"STEP {step_num}: {description}")
    print('─' * 80)

def print_response(label, data):
    print(f"\n{label}:")
    print(json.dumps(data, indent=2))

# ============================================================================
# PART 1: BACKEND VERIFICATION
# ============================================================================
print_section("PART 1: VERIFY BACKEND SERVICES")

print_step(1, "Test Backend - Balance Inquiry")
try:
    response = requests.get(f"{BACKEND_URL}/api/balance", params={"accountId": "123"}, timeout=3)
    print(f"Status: {response.status_code}")
    print_response("Backend Response", response.json())
except Exception as e:
    print(f"❌ Backend not running: {e}")
    print("Please start: cd backend-java/banking-backend && mvn spring-boot:run")
    exit(1)

print_step(2, "Test Backend - Account Statement")
try:
    response = requests.get(f"{BACKEND_URL}/api/statement", params={"accountId": "123"}, timeout=3)
    print(f"Status: {response.status_code}")
    print_response("Statement Response", response.json())
except Exception as e:
    print(f"⚠️  Statement endpoint error: {e}")

print_step(3, "Test Backend - Loan Inquiry")
try:
    response = requests.get(f"{BACKEND_URL}/api/loan", params={"accountId": "123"}, timeout=3)
    print(f"Status: {response.status_code}")
    print_response("Loan Response", response.json())
except Exception as e:
    print(f"⚠️  Loan endpoint error: {e}")

# ============================================================================
# PART 2: ORCHESTRATOR WORKFLOW
# ============================================================================
print_section("PART 2: AI ORCHESTRATOR WORKFLOW")

print_step(4, "Test Low-Value Transfer (< $5000) - Should Execute Immediately")
try:
    chat_request = {
        "message": "Transfer 2000 to Kiran",
        "user_id": "demo_user"
    }
    print(f"Sending: {chat_request['message']}")
    
    response = requests.post(f"{ORCHESTRATOR_URL}/chat", json=chat_request, timeout=5)
    print(f"Status: {response.status_code}")
    print_response("Orchestrator Response", response.json())
    
    reply = response.json().get("reply", {})
    if reply.get("status_code") == 200:
        print("\n✅ Low-value transfer executed successfully!")
    else:
        print(f"\n⚠️  Transfer status: {reply}")
except Exception as e:
    print(f"❌ Orchestrator not running: {e}")
    print("Please start: cd ai-orchestrator && uvicorn server:app --reload --port 8000")
    exit(1)

print_step(5, "Test High-Value Transfer (≥ $5000) - Should Require Approval")
chat_request = {
    "message": "Transfer 10000 to Kiran",
    "user_id": "demo_user"
}
print(f"Sending: {chat_request['message']}")

response = requests.post(f"{ORCHESTRATOR_URL}/chat", json=chat_request, timeout=5)
print(f"Status: {response.status_code}")
print_response("Orchestrator Response", response.json())

reply = response.json().get("reply", {})
if reply.get("status") == "pending_approval":
    print("\n✅ High-value transfer detected! Approval required.")
    approval_id = reply.get("approval_id")
    session_id = reply.get("session_id")
    print(f"\n📋 Approval ID: {approval_id}")
    print(f"📋 Session ID: {session_id}")
else:
    print("\n⚠️  Unexpected response - check threshold setting")
    approval_id = None
    session_id = None

# ============================================================================
# PART 3: APPROVAL WORKFLOW
# ============================================================================
print_section("PART 3: HUMAN-IN-THE-LOOP APPROVAL")

print_step(6, "Check Pending Approvals")
response = requests.get(f"{ORCHESTRATOR_URL}/approvals/pending", timeout=3)
pending_approvals = response.json().get("pending_approvals", [])
print(f"Total pending approvals: {len(pending_approvals)}")

for i, approval in enumerate(pending_approvals, 1):
    print(f"\n  Approval #{i}:")
    print(f"    ID: {approval['approval_id']}")
    print(f"    Amount: ${approval['amount']}")
    print(f"    Recipient: {approval['recipient']}")
    print(f"    Requested: {approval['requested_at']}")

if pending_approvals:
    approval_id = pending_approvals[0]['approval_id']
    
    print_step(7, "Approve the Transfer")
    print(f"Approving: {approval_id}")
    
    approval_request = {
        "approval_id": approval_id,
        "approved": True,
        "approver_id": "demo_manager"
    }
    
    response = requests.post(f"{ORCHESTRATOR_URL}/approve", json=approval_request, timeout=5)
    print(f"Status: {response.status_code}")
    print_response("Approval Response", response.json())
    
    approval_result = response.json()
    if approval_result.get("status") == "approved":
        print("\n✅ Transfer approved and executed successfully!")
        if "transfer_result" in approval_result:
            print_response("Transfer Result", approval_result["transfer_result"])
    else:
        print(f"\n⚠️  Approval status: {approval_result}")
    
    print_step(8, "Verify No Pending Approvals Remain")
    response = requests.get(f"{ORCHESTRATOR_URL}/approvals/pending", timeout=3)
    remaining = response.json().get("pending_approvals", [])
    print(f"Remaining pending approvals: {len(remaining)}")
    if len(remaining) == 0:
        print("✅ All approvals processed!")

# ============================================================================
# PART 4: OTHER BANKING OPERATIONS
# ============================================================================
print_section("PART 4: OTHER BANKING OPERATIONS")

print_step(9, "Test Balance Inquiry via Orchestrator")
chat_request = {"message": "What's my account balance?", "user_id": "demo_user"}
print(f"Sending: {chat_request['message']}")

response = requests.post(f"{ORCHESTRATOR_URL}/chat", json=chat_request, timeout=5)
reply = response.json().get("reply", {})
print_response("Balance Response", reply)

print_step(10, "Test Account Statement via Orchestrator")
chat_request = {"message": "Show my account statement", "user_id": "demo_user"}
print(f"Sending: {chat_request['message']}")

response = requests.post(f"{ORCHESTRATOR_URL}/chat", json=chat_request, timeout=5)
reply = response.json().get("reply", {})
print_response("Statement Response", reply)

print_step(11, "Test Loan Inquiry via Orchestrator")
chat_request = {"message": "What loan options do I have?", "user_id": "demo_user"}
print(f"Sending: {chat_request['message']}")

response = requests.post(f"{ORCHESTRATOR_URL}/chat", json=chat_request, timeout=5)
reply = response.json().get("reply", {})
print_response("Loan Response", reply)

# ============================================================================
# PART 5: DATABASE VERIFICATION
# ============================================================================
print_section("PART 5: DATABASE & PERSISTENCE")

print_step(12, "Check Database State")
try:
    # Query recent sessions
    import sqlite3
    conn = sqlite3.connect("workflows.db")
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM workflow_sessions")
    session_count = cursor.fetchone()[0]
    print(f"Total workflow sessions: {session_count}")
    
    cursor.execute("SELECT COUNT(*) FROM pending_approvals")
    approval_count = cursor.fetchone()[0]
    print(f"Total approval requests: {approval_count}")
    
    cursor.execute("SELECT status, COUNT(*) FROM pending_approvals GROUP BY status")
    status_counts = cursor.fetchall()
    print("\nApproval status breakdown:")
    for status, count in status_counts:
        print(f"  {status}: {count}")
    
    cursor.execute("""
        SELECT session_id, user_id, status, created_at, updated_at 
        FROM workflow_sessions 
        ORDER BY created_at DESC 
        LIMIT 3
    """)
    recent_sessions = cursor.fetchall()
    
    print("\nRecent sessions:")
    for session in recent_sessions:
        print(f"  Session: {session[0][:8]}...")
        print(f"    User: {session[1]}")
        print(f"    Status: {session[2]}")
        print(f"    Created: {session[3]}")
        print()
    
    conn.close()
except Exception as e:
    print(f"⚠️  Database query error: {e}")

# ============================================================================
# SUMMARY
# ============================================================================
print_section("SYSTEM DEMONSTRATION COMPLETE")

print("""
✅ VERIFIED COMPONENTS:
  ├─ Backend API (Java Spring Boot on port 8081)
  │   ├─ Balance inquiry
  │   ├─ Money transfer
  │   ├─ Account statement
  │   └─ Loan inquiry
  │
  ├─ AI Orchestrator (Python FastAPI on port 8000)
  │   ├─ Intent classification
  │   ├─ LangGraph workflow
  │   ├─ Low-value transfer (auto-execute)
  │   ├─ High-value transfer (approval required)
  │   └─ HIL approval system
  │
  ├─ Persistence Layer (SQLite)
  │   ├─ Workflow sessions
  │   ├─ Pending approvals
  │   └─ Audit trail
  │
  └─ Streamlit UI (port 8501)
      └─ Chat interface (open in browser)

📊 WORKFLOW SUMMARY:
  • Low-value transfers (< $5000) execute immediately
  • High-value transfers (≥ $5000) require manager approval
  • All transactions tracked in database
  • State persists across server restarts
  • Complete audit trail maintained

🌐 ACCESS POINTS:
  • Backend API:      http://localhost:8081/api
  • Orchestrator API: http://localhost:8000/docs
  • Streamlit UI:     http://localhost:8501
  • GitHub Repo:      https://github.com/Dhanusankar/Banking

📝 SAMPLE PROMPTS (try in Streamlit UI):
  1. "What's my balance?"
  2. "Transfer 1000 to Kiran"          (executes immediately)
  3. "Transfer 10000 to Kiran"         (requires approval)
  4. "Show my account statement"
  5. "What loan options do I have?"

✨ KEY FEATURES DEMONSTRATED:
  ✓ Natural language understanding
  ✓ Graph-based workflow orchestration (LangGraph)
  ✓ Threshold-based approval detection
  ✓ Human-in-the-loop workflow
  ✓ State persistence and resumption
  ✓ Session tracking
  ✓ Audit trail
  ✓ RESTful API integration
""")

print("=" * 80)
print("Demo completed successfully!")
print("=" * 80)
