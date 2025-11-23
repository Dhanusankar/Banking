# 🧪 How to Test Low-Confidence HIL Trigger

## What You're Testing:
**Node-3**: If `confidence < 0.80` → Pause workflow for user confirmation

## Prerequisites:
1. ✅ Ollama service running
2. ✅ Backend running (port 8081)
3. ✅ Orchestrator running (port 8000)
4. ✅ UI running (port 8501)

---

## 🚀 Quick Start Test

### Start Services:
```powershell
# Terminal 1: Ollama
ollama serve

# Terminal 2: Backend
cd backend-java\banking-backend
mvn spring-boot:run

# Terminal 3: Orchestrator
cd ai-orchestrator
python server_v2.py

# Terminal 4: UI
cd ui
streamlit run ui_v2.py
```

---

## ✅ Test Case 1: HIGH Confidence (No HIL)

### Input:
```
What is my balance?
```

### Expected Behavior:
- ✅ LLM returns confidence: **0.90+**
- ✅ Workflow proceeds automatically
- ✅ NO approval panel appears
- ✅ Response: "💰 Your current balance is $50,000.00"

### What to Watch in Orchestrator Logs:
```
🤖 LLM Intent: balance_inquiry (confidence: 0.95)
✓ High confidence (0.95) - Proceeding automatically
🔀 High confidence - routing to: balance_inquiry
```

---

## ⏸️ Test Case 2: LOW Confidence (Triggers HIL)

### Input:
```
Send some money
```

### Expected Behavior:
- ⚠️ LLM returns confidence: **0.50-0.70** (vague request)
- ⏸️ Workflow PAUSES at confidence_check node
- ⚠️ **Approval panel appears on right side of UI**
- 📋 Shows: "Transfer requires approval"

### What to Watch in Orchestrator Logs:
```
🤖 LLM Intent: money_transfer (confidence: 0.65)
⚠️ Low confidence (0.65 < 0.80) - Requires human approval
🔀 Routing to HIL due to low confidence
⏸️ Transfer paused for approval: $0
```

### What You'll See in UI:
- Right panel header: **"⚠️ Pending Approvals"**
- Approval card with:
  - Amount: $0 (or extracted amount)
  - Recipient: unknown (or extracted recipient)
  - Session ID
  - ✅ Approve / ❌ Reject buttons

---

## ⏸️ Test Case 3: NON-Banking Request (Triggers HIL)

### Input:
```
Help me
```

### Expected Behavior:
- ⚠️ LLM returns confidence: **< 0.50** (unclear/fallback)
- ⏸️ Workflow PAUSES
- ⚠️ Approval required due to low confidence

### Orchestrator Logs:
```
🤖 LLM Intent: fallback (confidence: 0.30)
⚠️ Low confidence (0.30 < 0.80) - Requires human approval
🔀 Routing to HIL due to low confidence
```

---

## ⏸️ Test Case 4: Partial Information (Triggers HIL)

### Input:
```
Transfer to John
```
(Missing amount)

### Expected Behavior:
- ⚠️ Confidence: **0.60-0.75** (incomplete request)
- ⏸️ HIL triggered
- Shows: Recipient "John", Amount "0" or extracted

---

## ❌ Test Case 5: Typo but Clear (HIGH Confidence)

### Input:
```
tansfer 1000 to Kiran
```
(Typo: "tansfer" instead of "transfer")

### Expected Behavior:
- ✅ LLM handles typo gracefully
- ✅ Confidence: **0.85-0.95**
- ✅ Auto-processes (no HIL for typos if clear intent)
- ✅ But WILL trigger HIL if amount ≥ $5000

---

## 🔍 How to Debug in Real-Time

### 1. Watch Orchestrator Terminal:
Look for these log lines:
```
🤖 LLM Classification: intent=X, confidence=0.XX
   Entities: {...}
⚠️ Low confidence (0.XX < 0.80) - Requires human approval
🔀 Routing to HIL due to low confidence
⏸️ Transfer paused for approval: $X
```

### 2. Check banking_graph.py Node Execution:
The flow goes:
```
validate_input_node
  ↓ (calls Llama-3)
confidence_check_node
  ↓
route_after_confidence_check
  ↓
money_transfer_hil (if low confidence)
  ↓ (sets _halt=True, workflow pauses)
END (UI shows approval panel)
```

### 3. Inspect Network Tab:
- Open browser DevTools (F12)
- Go to Network tab
- Send "Send some money"
- Check `/chat` response:
```json
{
  "session_id": "...",
  "reply": {
    "status": "PENDING_APPROVAL",
    "message": "Transfer requires approval",
    "amount": 0,
    "recipient": "unknown",
    "approval_id": "..."
  }
}
```

---

## 🎯 Confidence Threshold Logic

In `banking_graph.py` → `confidence_check_node`:
```python
threshold = 0.80  # The magic number!

if confidence < threshold:
    state["needs_approval"] = True
    state["approval_reason"] = f"Low LLM confidence: {confidence:.2f}"
```

### Examples:
| Request | LLM Confidence | HIL Triggered? |
|---------|----------------|----------------|
| "What's my balance?" | 0.95 | ❌ No |
| "Transfer 1000 to John" | 0.90 | ❌ No |
| "Send some cash" | 0.65 | ✅ **YES** |
| "Help me" | 0.30 | ✅ **YES** |
| "I need assistance" | 0.25 | ✅ **YES** |

---

## 🐛 Troubleshooting

### Issue: "Connection timeout"
- **Cause**: Ollama not running or slow
- **Fix**: Start Ollama (`ollama serve`) and wait 30s

### Issue: "HIL not triggering"
- **Cause**: Ollama returning high confidence for everything
- **Fix**: Use MORE vague requests like "do something" or "help"

### Issue: "Always shows fallback"
- **Cause**: LLM API failed, using rule-based fallback
- **Fix**: Check Ollama logs, ensure llama3 model is pulled

---

## 📊 Full Test Sequence

Run these 5 tests in order:

1. **"What is my balance?"** → Expect: **Auto-processed** (0.95 confidence)
2. **"Transfer 1000 to Kiran"** → Expect: **Auto-processed** (0.90 confidence)
3. **"Send some money"** → Expect: **⏸️ HIL paused** (0.65 confidence)
4. **"Help me"** → Expect: **⏸️ HIL paused** (0.30 confidence)
5. **"Transfer 10000 to Sarah"** → Expect: **⏸️ HIL paused** (amount ≥ $5000, even if 0.95 confidence)

Test #3 and #4 prove your **Node-3: confidence < threshold → pause** logic works!

---

## ✅ Success Criteria

You've successfully tested Node-3 if you see:

1. ⏸️ Workflow pauses for vague requests
2. ⚠️ "Pending Approvals" panel appears in UI
3. 📋 Approval form shows amount/recipient
4. 📊 Orchestrator logs show "Low confidence" message
5. 🔀 Routing goes to HIL instead of direct execution
6. ✅ Approve/Reject buttons work
7. ▶️ Workflow resumes after approval

**That's your confidence-based routing working!** 🎉
