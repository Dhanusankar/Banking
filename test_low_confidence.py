"""
Test script to demonstrate low-confidence HIL trigger.
Tests Node-3: If confidence < 0.80 → Pause for approval
"""
import requests
import json
import time

ORCHESTRATOR_URL = "http://localhost:8000"

def test_low_confidence_hil():
    """Test cases that should trigger low-confidence HIL."""
    
    print("=" * 60)
    print("🧪 TESTING LOW CONFIDENCE HIL TRIGGER")
    print("=" * 60)
    
    test_cases = [
        {
            "message": "Send some money",
            "description": "Vague transfer (no amount/recipient)",
            "expected_confidence": "< 0.80",
            "expected_hil": True
        },
        {
            "message": "Help me",
            "description": "Unclear intent",
            "expected_confidence": "< 0.50",
            "expected_hil": True
        },
        {
            "message": "I need assistance",
            "description": "Non-banking request",
            "expected_confidence": "< 0.50",
            "expected_hil": True
        },
        {
            "message": "What is my balance?",
            "description": "Clear intent (HIGH confidence)",
            "expected_confidence": "> 0.80",
            "expected_hil": False
        },
        {
            "message": "Transfer 1000 to Kiran",
            "description": "Clear transfer (HIGH confidence)",
            "expected_confidence": "> 0.80",
            "expected_hil": False
        }
    ]
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n{'='*60}")
        print(f"Test Case {i}: {test['description']}")
        print(f"{'='*60}")
        print(f"📝 Message: '{test['message']}'")
        print(f"🎯 Expected Confidence: {test['expected_confidence']}")
        print(f"🚦 Expected HIL: {'YES' if test['expected_hil'] else 'NO'}")
        print("-" * 60)
        
        # Send request
        try:
            response = requests.post(
                f"{ORCHESTRATOR_URL}/chat",
                json={
                    "message": test["message"],
                    "user_id": f"test_user_{i}"
                },
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                reply = data.get("reply", {})
                session_id = data.get("session_id", "N/A")
                
                # Check if HIL was triggered
                status = reply.get("status")
                is_pending = status == "PENDING_APPROVAL"
                
                print(f"✅ Response received!")
                print(f"   Session ID: {session_id[:8]}...")
                print(f"   Status: {status}")
                
                if is_pending:
                    print(f"   ⏸️  HIL TRIGGERED - Workflow paused for approval")
                    print(f"   Amount: ${reply.get('amount', 0)}")
                    print(f"   Recipient: {reply.get('recipient', 'N/A')}")
                    print(f"   Approval ID: {reply.get('approval_id', 'N/A')}")
                else:
                    print(f"   ▶️  Auto-processed (no HIL)")
                    intent = reply.get("intent", "unknown")
                    print(f"   Intent: {intent}")
                
                # Validate expectation
                if is_pending == test['expected_hil']:
                    print(f"   ✅ PASS: HIL behavior matches expectation")
                else:
                    print(f"   ❌ FAIL: Expected HIL={test['expected_hil']}, Got HIL={is_pending}")
                
            else:
                print(f"❌ Error: HTTP {response.status_code}")
                print(f"   {response.text[:200]}")
                
        except requests.exceptions.Timeout:
            print(f"⏱️  Timeout (LLM may be slow or Ollama not running)")
        except Exception as e:
            print(f"❌ Error: {e}")
        
        time.sleep(1)  # Brief pause between tests
    
    print("\n" + "=" * 60)
    print("🏁 TEST COMPLETE")
    print("=" * 60)
    print("\n📊 HOW TO VERIFY IN UI:")
    print("   1. Open http://localhost:8501")
    print("   2. Type: 'Send some money'")
    print("   3. Look for '⚠️ Pending Approvals' panel on right")
    print("   4. Should show approval form with amount/recipient")
    print("\n📊 HOW TO VERIFY IN LOGS:")
    print("   Check orchestrator terminal for:")
    print("   - '🤖 LLM Intent: ... (confidence: 0.XX)'")
    print("   - '⚠️ Low confidence (0.XX < 0.80) - Requires human approval'")
    print("   - '🔀 Routing to HIL due to low confidence'")


if __name__ == "__main__":
    print("\n⏳ Waiting 3 seconds for services to be ready...")
    time.sleep(3)
    
    # Check if orchestrator is running
    try:
        health = requests.get(f"{ORCHESTRATOR_URL}/health", timeout=2)
        if health.status_code == 200:
            print("✅ Orchestrator is ready!\n")
            test_low_confidence_hil()
        else:
            print("❌ Orchestrator not responding. Start it first:")
            print("   cd ai-orchestrator")
            print("   python server_v2.py")
    except:
        print("❌ Orchestrator not running. Start it first:")
        print("   cd ai-orchestrator")
        print("   python server_v2.py")
