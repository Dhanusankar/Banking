# Banking AI POC - Cloud Deployment Guide

## 🚀 Quick Deploy to Render.com (Recommended)

### Prerequisites
- GitHub account
- Render.com account (free)
- Repository pushed to GitHub

---

## Option 1: One-Click Deploy with Blueprint

### Step 1: Push to GitHub
```bash
cd c:\Users\dhanu\bank_ai\banking-ai-poc
git add .
git commit -m "Prepare for Render deployment"
git push origin master
```

### Step 2: Deploy via Render Dashboard
1. Go to https://render.com/
2. Click **"New"** → **"Blueprint"**
3. Connect your GitHub repository: `Dhanusankar/Banking`
4. Render will detect `render.yaml` and create all 3 services automatically
5. Wait 5-10 minutes for build & deploy

### Step 3: Get Service URLs
After deployment, you'll get 3 URLs:
- **Backend:** `https://banking-backend-xxxx.onrender.com`
- **Orchestrator:** `https://banking-orchestrator-xxxx.onrender.com`
- **UI:** `https://banking-ui-xxxx.onrender.com` ← **Open this!**

---

## Option 2: Manual Service Creation

If blueprint fails, deploy each service manually:

### Service 1: Java Backend

1. **Render Dashboard** → **New Web Service**
2. **Connect GitHub repo:** `Dhanusankar/Banking`
3. **Configure:**
   ```
   Name:              banking-backend
   Region:            Oregon (US West)
   Branch:            master
   Root Directory:    backend-java/banking-backend
   Runtime:           Java
   Build Command:     mvn clean package -DskipTests
   Start Command:     java -jar target/banking-backend-0.0.1-SNAPSHOT.jar
   ```
4. **Environment Variables:**
   ```
   SERVER_PORT=8081
   JAVA_OPTS=-Xmx512m
   ```
5. **Deploy** → Wait for "Live" status
6. **Copy URL:** e.g., `https://banking-backend-xxxx.onrender.com`

---

### Service 2: AI Orchestrator

1. **New Web Service**
2. **Connect repo:** `Dhanusankar/Banking`
3. **Configure:**
   ```
   Name:              banking-orchestrator
   Region:            Oregon
   Branch:            master
   Root Directory:    ai-orchestrator
   Runtime:           Python 3.11
   Build Command:     pip install -r requirements_v2.txt
   Start Command:     uvicorn server_v2:app --host 0.0.0.0 --port 8000
   ```
4. **Environment Variables:**
   ```
   BACKEND_URL=https://banking-backend-xxxx.onrender.com
   PORT=8000
   PYTHONUNBUFFERED=1
   ```
5. **Deploy** → Wait for "Live"
6. **Copy URL:** e.g., `https://banking-orchestrator-xxxx.onrender.com`

---

### Service 3: Streamlit UI

1. **New Web Service**
2. **Connect repo:** `Dhanusankar/Banking`
3. **Configure:**
   ```
   Name:              banking-ui
   Region:            Oregon
   Branch:            master
   Root Directory:    ui
   Runtime:           Python 3.11
   Build Command:     pip install -r requirements.txt
   Start Command:     streamlit run ui_v2.py --server.port 8501 --server.address 0.0.0.0
   ```
4. **Environment Variables:**
   ```
   ORCHESTRATOR_URL=https://banking-orchestrator-xxxx.onrender.com
   PORT=8501
   ```
5. **Deploy** → Wait for "Live"
6. **Open URL:** e.g., `https://banking-ui-xxxx.onrender.com`

---

## 🔧 Configuration Updates Needed

### 1. Update `banking_graph.py`
```python
# Before (local):
BACKEND_URL = "http://localhost:8081"

# After (cloud):
BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8081")
```

### 2. Update `ui_v2.py`
```python
# Before (local):
BASE_URL = "http://localhost:8000"

# After (cloud):
BASE_URL = os.environ.get("ORCHESTRATOR_URL", "http://localhost:8000")
```

### 3. Update `application.properties`
```properties
# Add for cloud deployment
server.port=${PORT:8081}
```

---

## 🎯 Testing Deployed Services

### Test Backend
```bash
curl https://banking-backend-xxxx.onrender.com/api/balance?accountId=123
# Expected: {"accountId":"123","balance":50000.0}
```

### Test Orchestrator
```bash
curl https://banking-orchestrator-xxxx.onrender.com/health
# Expected: {"status":"healthy"}
```

### Test UI
Open browser: `https://banking-ui-xxxx.onrender.com`
- Should load Streamlit interface
- Try: "What's my balance?"
- Try: "Transfer 1000 to Kiran"

---

## 📊 Monitoring & Logs

### View Logs (Render Dashboard)
1. Click service name
2. Go to **"Logs"** tab
3. See real-time output

### Common Issues

**Issue:** Service won't start
- **Check:** Build logs for errors
- **Fix:** Ensure dependencies in `requirements_v2.txt` / `pom.xml`

**Issue:** UI can't connect to orchestrator
- **Check:** Environment variable `ORCHESTRATOR_URL` is set
- **Fix:** Update with correct orchestrator URL

**Issue:** Orchestrator can't connect to backend
- **Check:** Environment variable `BACKEND_URL` is set
- **Fix:** Update with correct backend URL

**Issue:** Services sleeping (free tier)
- **Behavior:** Render free tier sleeps after 15 min inactivity
- **Fix:** First request takes ~30 seconds (cold start)
- **Upgrade:** $7/month for always-on

---

## 🔐 Security Considerations

### For Production Deployment:

1. **Add Authentication:**
   - JWT tokens for API
   - OAuth for UI login
   - API keys for service-to-service

2. **Enable HTTPS:**
   - Render provides free SSL automatically
   - Force HTTPS redirects

3. **Environment Secrets:**
   - Use Render's secret management
   - Never commit API keys to Git

4. **Database:**
   - Switch from SQLite to PostgreSQL
   - Add Redis for checkpoints
   - Enable backups

5. **Rate Limiting:**
   - Add rate limiting middleware
   - Prevent abuse

---

## 💰 Cost Estimate

### Free Tier (Current Setup)
- **Backend:** Free (750 hrs/month)
- **Orchestrator:** Free (750 hrs/month)
- **UI:** Free (750 hrs/month)
- **Total:** $0/month

**Limitations:**
- Services sleep after 15 min inactivity
- 512 MB RAM per service
- No custom domains

### Paid Tier (Production)
- **Backend:** $7/month (always-on)
- **Orchestrator:** $7/month (always-on)
- **UI:** $7/month (always-on)
- **PostgreSQL:** $7/month (1 GB)
- **Total:** $28/month

**Benefits:**
- Always-on (no cold starts)
- 2 GB RAM per service
- Custom domains included
- Auto-scaling

---

## 🎬 Demo Script

After deployment, demo the system:

### 1. Balance Inquiry
```
User: "What's my balance?"
Bot: "Your balance is $50,000.00"
✓ 2 checkpoints saved
```

### 2. Low-Value Transfer
```
User: "Transfer 1000 to Kiran"
Bot: "✓ Transferred $1,000.00 from 123 to kiran"
✓ Auto-approved (< $5000)
✓ 5 checkpoints saved
```

### 3. High-Value Transfer (Approval Required)
```
User: "Transfer 6000 to Kiran"
Bot: "⏸️ Transfer requires manager approval"
[Approval Panel Appears]
Manager: [Clicks Approve]
Bot: "✓ Transfer approved by manager@bank.com"
Bot: "✓ Transferred $6,000.00 from 123 to kiran"
✓ 7 checkpoints saved
```

### 4. Show Features
- **Session tracking** in sidebar
- **Checkpoint counter** updates in real-time
- **Execution history** shows all nodes
- **Approval panel** appears dynamically
- **Workflow status** changes (ACTIVE → PENDING → COMPLETED)

---

## 🔄 Continuous Deployment

Enable auto-deploy on Git push:

1. In Render service settings
2. Enable **"Auto-Deploy"**
3. Select branch: `master`
4. Now: `git push` → Render auto-deploys

---

## 📱 Alternative Platforms

### Railway.app
- Similar to Render
- Better for monorepos
- $5 credit free

### Heroku
- More expensive ($7/dyno)
- Easier PostgreSQL setup
- Better CLI tools

### AWS (Advanced)
- ECS for containers
- RDS for database
- More complex, more control

### Google Cloud Run
- Serverless containers
- Pay per request
- Great for variable traffic

---

## 🎯 Next Steps After Deployment

1. **Share URL** with stakeholders
2. **Collect feedback** on features
3. **Monitor usage** via Render dashboard
4. **Add custom domain** (optional)
5. **Set up alerts** for downtime
6. **Add analytics** (PostHog, Mixpanel)
7. **Enable authentication** for security
8. **Switch to PostgreSQL** for production data

---

## 📞 Support

If deployment fails:
- Check Render service logs
- Verify GitHub repo is public or Render has access
- Ensure `requirements_v2.txt` has all dependencies
- Test locally first: `docker-compose up`

---

## ✅ Deployment Checklist

- [ ] Code pushed to GitHub
- [ ] `render.yaml` committed
- [ ] Environment variables configured
- [ ] Backend deployed & healthy
- [ ] Orchestrator deployed & healthy
- [ ] UI deployed & accessible
- [ ] Test balance inquiry
- [ ] Test low-value transfer
- [ ] Test high-value transfer with approval
- [ ] Check logs for errors
- [ ] Share URL with team

---

**Estimated Total Time:** 15-30 minutes (mostly waiting for builds)

**Your URLs after deployment:**
- UI: https://banking-ui-xxxx.onrender.com
- API Docs: https://banking-orchestrator-xxxx.onrender.com/docs
- Backend Health: https://banking-backend-xxxx.onrender.com/api/balance?accountId=123
