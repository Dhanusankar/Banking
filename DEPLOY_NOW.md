# 🚀 Quick Deploy to Render.com

## ✅ Pre-Deployment Checklist (COMPLETED)
- ✓ Code pushed to GitHub: `Dhanusankar/Banking`
- ✓ `render.yaml` configured
- ✓ Environment variables set up
- ✓ Health checks configured
- ✓ Build commands ready

---

## 🎯 Deploy Now (3 Steps)

### Step 1: Create Render Account
Go to: https://render.com/
- Sign up with GitHub
- Authorize Render to access your repos

### Step 2: Deploy via Blueprint (One-Click)
1. Dashboard → Click **"New"** → Select **"Blueprint"**
2. Connect repository: `Dhanusankar/Banking`
3. Render auto-detects `render.yaml`
4. Click **"Apply"**
5. ☕ Wait 10-15 minutes

### Step 3: Get URLs & Test
After deployment completes:
```
✓ Banking Backend:      https://banking-backend-xxxx.onrender.com
✓ Banking Orchestrator: https://banking-orchestrator-xxxx.onrender.com  
✓ Banking UI:           https://banking-ui-xxxx.onrender.com
```

**Open the UI URL** → Start chatting!

---

## 🧪 Quick Test Commands

### Test Backend
```bash
curl https://banking-backend-xxxx.onrender.com/api/balance?accountId=123
```
Expected: `{"accountId":"123","balance":50000.0}`

### Test Orchestrator
```bash
curl https://banking-orchestrator-xxxx.onrender.com/health
```
Expected: `{"status":"healthy"}`

### Test UI
Open in browser: `https://banking-ui-xxxx.onrender.com`

---

## 🎬 Demo Script (Share This URL)

**Try these in order:**

1. **Balance Check**
   ```
   "What's my balance?"
   ```
   → Should return: $50,000.00

2. **Low-Value Transfer** (Auto-Approved)
   ```
   "Transfer 1000 to Kiran"
   ```
   → Executes immediately (< $5000 threshold)

3. **High-Value Transfer** (Needs Approval)
   ```
   "Transfer 6000 to Kiran"
   ```
   → Approval panel appears
   → Click "Approve"
   → Transfer executes

4. **Show Features**
   - Session tracking (sidebar)
   - Checkpoint counter
   - Execution history
   - Workflow status

---

## 📊 Architecture Deployed

```
┌─────────────────────────────────────────────────┐
│  Streamlit UI (Port 8501)                       │
│  https://banking-ui-xxxx.onrender.com          │
└──────────────────┬──────────────────────────────┘
                   │ REST API
                   ▼
┌─────────────────────────────────────────────────┐
│  FastAPI Orchestrator (Port 8000)              │
│  https://banking-orchestrator-xxxx.onrender.com│
│  - LangGraph workflow engine                   │
│  - Checkpointing system                        │
│  - HIL approval logic                          │
│  - Session management                          │
└──────────────────┬──────────────────────────────┘
                   │ REST API
                   ▼
┌─────────────────────────────────────────────────┐
│  Spring Boot Backend (Port 8081)               │
│  https://banking-backend-xxxx.onrender.com     │
│  - Account management                          │
│  - Transfer execution                          │
│  - Balance inquiry                             │
└─────────────────────────────────────────────────┘
```

---

## ⚠️ Important Notes

### Free Tier Limitations
- Services **sleep after 15 min** of inactivity
- First request after sleep takes ~30 seconds (cold start)
- 512 MB RAM per service
- Shared CPU

### Cold Start Behavior
```
User visits UI → Wakes up UI service (5s)
                → Wakes up Orchestrator (10s)
                → Wakes up Backend (15s)
Total: ~30 seconds first load
```

After wake-up: **Instant response** ⚡

### Upgrade to Paid ($7/month per service)
- Always-on (no cold starts)
- 2 GB RAM
- Dedicated CPU
- Custom domains

---

## 🔧 Environment Variables (Auto-Configured)

### Backend Service
```
SERVER_PORT=8081
JAVA_OPTS=-Xmx512m
```

### Orchestrator Service
```
BACKEND_URL=https://banking-backend-xxxx.onrender.com
PORT=8000
PYTHONUNBUFFERED=1
```

### UI Service
```
ORCHESTRATOR_URL=https://banking-orchestrator-xxxx.onrender.com
PORT=8501
```

---

## 📱 Share With Stakeholders

**Subject:** Banking AI POC - Live Demo

Hi Team,

I've deployed our Banking AI POC to the cloud. You can try it here:

🔗 **Demo URL:** https://banking-ui-xxxx.onrender.com

**What it does:**
- Natural language banking operations
- Human-in-the-loop approvals for high-value transfers ($5000+)
- Complete checkpoint system (7 per workflow)
- Session management & conversation history
- Real-time approval panel

**Try these commands:**
1. "What's my balance?"
2. "Transfer 1000 to Kiran" (auto-approved)
3. "Transfer 6000 to Kiran" (needs approval)

**Note:** First load may take 30 seconds (free tier cold start). After that, it's instant.

**Tech Stack:**
- Java 17 + Spring Boot (Backend)
- Python + FastAPI + LangGraph (AI Orchestrator)
- Streamlit (UI)
- Deployed on Render.com

Let me know your feedback!

---

## 🐛 Troubleshooting

### Service Won't Start
- Check Render logs: Dashboard → Service → Logs tab
- Look for build errors or missing dependencies

### UI Can't Connect to Orchestrator
- Verify `ORCHESTRATOR_URL` env var is set correctly
- Check orchestrator is "Live" status

### Cold Start Takes Too Long
- Normal behavior on free tier
- Upgrade to paid plan for always-on

### Database Issues
- SQLite runs in-memory (data resets on redeploy)
- For persistence, upgrade to PostgreSQL (see DEPLOYMENT_GUIDE.md)

---

## 🎯 Next Steps

1. **Share Demo URL** with stakeholders
2. **Collect Feedback** on features
3. **Monitor Usage** via Render dashboard
4. **Consider Upgrades:**
   - Always-on services ($7/month each)
   - PostgreSQL database ($7/month)
   - Custom domain (free with paid tier)

---

## 📚 Full Documentation

- **Complete Guide:** `DEPLOYMENT_GUIDE.md`
- **Architecture:** `SYSTEM_ARCHITECTURE.md`
- **Quick Start:** `QUICKSTART_V2.md`
- **Workflow Example:** `WORKFLOW_EXAMPLE.md`

---

## 💰 Cost Summary

**Current Setup (Free Tier):**
- Backend: $0/month
- Orchestrator: $0/month
- UI: $0/month
- **Total: FREE** ✨

**Production Setup (Paid Tier):**
- 3 Services: $21/month
- PostgreSQL: $7/month
- **Total: $28/month**

---

## ✅ Deployment Complete!

Your Banking AI POC is now live and accessible worldwide! 🌍

**Next:** Open the UI URL and start demoing! 🚀
