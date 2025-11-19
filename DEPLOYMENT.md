# Deployment Guide - Banking AI POC

## ⚠️ Important: GitHub Pages Cannot Host This Application

**GitHub Pages only serves static HTML/CSS/JS files.** This POC requires:
- Java Spring Boot backend (dynamic server)
- Python FastAPI orchestrator (dynamic server)
- Streamlit UI (Python web app)

**Use one of the deployment options below instead.**

---

## Recommended Deployment Options

### Option 1: Docker Compose (Easiest for Testing)

**Best for:** Local testing, development environments, or VPS deployment

```bash
# Clone the repository
git clone https://github.com/Dhanusankar/Banking.git
cd Banking

# Start all services
docker-compose up --build

# Access:
# - Backend: http://localhost:8081
# - Orchestrator: http://localhost:8000
# - UI: http://localhost:8501
```

**Pros:**
- ✅ One command starts everything
- ✅ Services communicate via internal network
- ✅ Easy to deploy to any Docker-compatible host

**Cons:**
- ❌ Requires Docker installed
- ❌ Not suitable for free tier cloud hosting

---

### Option 2: Streamlit Cloud + Cloud Backends (Recommended for Production)

**Best for:** Public demos, POC presentations, free hosting

#### Step 1: Deploy Backend (Choose One)

##### A. Render (Recommended - Free Tier Available)
1. Go to [render.com](https://render.com)
2. Create new **Web Service**
3. Connect GitHub repo: `Dhanusankar/Banking`
4. Settings:
   - **Name:** banking-backend
   - **Region:** Choose nearest
   - **Branch:** master
   - **Root Directory:** `backend-java/banking-backend`
   - **Environment:** Docker
   - **Dockerfile path:** `Dockerfile`
   - **Port:** 8081
5. Click **Create Web Service**
6. Wait for deployment (5-10 minutes)
7. Copy the URL: `https://banking-backend-XXXX.onrender.com`

##### B. Railway (Alternative)
1. Go to [railway.app](https://railway.app)
2. New Project → Deploy from GitHub
3. Select `Dhanusankar/Banking`
4. Add service: Backend
   - Root: `backend-java/banking-backend`
   - Use Dockerfile
5. Set port: 8081
6. Copy generated URL

#### Step 2: Deploy Orchestrator

1. On Render/Railway, create another **Web Service**
2. Settings:
   - **Root Directory:** `ai-orchestrator`
   - **Environment:** Docker
   - **Port:** 8000
3. Deploy and copy URL: `https://orchestrator-XXXX.onrender.com`

#### Step 3: Deploy UI on Streamlit Cloud

1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Click **New app**
3. Settings:
   - **Repository:** `Dhanusankar/Banking`
   - **Branch:** `master`
   - **Main file path:** `ui/ui.py`
   - **Python version:** 3.11
4. **Advanced settings** → **Secrets**:
   ```toml
   ORCHESTRATOR_URL = "https://orchestrator-XXXX.onrender.com/chat"
   ```
   (Replace with your actual orchestrator URL from Step 2)
5. Click **Deploy**
6. Share the generated URL: `https://your-app.streamlit.app`

---

### Option 3: ngrok for Quick Testing (Local Backend, Public UI)

**Best for:** Quick demos without deploying backend

#### Prerequisites
- Download [ngrok](https://ngrok.com/download)
- Backend and orchestrator running locally

#### Steps

```powershell
# Terminal 1: Start backend
cd backend-java/banking-backend
mvn spring-boot:run

# Terminal 2: Start orchestrator
cd ai-orchestrator
uvicorn server:app --port 8000

# Terminal 3: Expose orchestrator via ngrok
ngrok http 8000
# Copy the forwarding URL: https://abcd-1234.ngrok.io

# Terminal 4: Start UI with ngrok URL
cd ui
$env:ORCHESTRATOR_URL = 'https://abcd-1234.ngrok.io/chat'
streamlit run ui.py
```

Now you can:
- Share the ngrok URL with anyone
- Deploy UI to Streamlit Cloud with the ngrok URL as `ORCHESTRATOR_URL`

**Note:** ngrok free tier URLs expire after 2 hours and change on restart.

---

### Option 4: Full Cloud Deployment (All Services)

**Best for:** Production applications

| Component | Service Options | Cost |
|-----------|----------------|------|
| **Backend** | AWS Elastic Beanstalk, Azure App Service, Google Cloud Run | Pay-as-you-go |
| **Orchestrator** | AWS Lambda + API Gateway, Azure Functions, Google Cloud Functions | Pay-as-you-go |
| **UI** | Streamlit Cloud | Free |

**Deployment steps vary by provider** - refer to their documentation for Docker/Java/Python deployments.

---

## Deployment Checklist

Before deploying, ensure:

- [ ] All three services start successfully locally
- [ ] Backend responds to: `curl http://localhost:8081/api/balance?accountId=123`
- [ ] Orchestrator responds to: `curl http://localhost:8000/docs`
- [ ] UI connects to orchestrator (test locally first)
- [ ] CORS is enabled on backend (`@CrossOrigin` annotation present)
- [ ] `ORCHESTRATOR_URL` is configured in UI for cloud deployment
- [ ] `.gitignore` excludes secrets and build artifacts

---

## Testing Deployed Application

Once deployed, test with these prompts:

```
1. "What's my balance?"
   Expected: Balance information for account 123

2. "Transfer 2000 to Kiran"
   Expected: Transfer confirmation

3. "Show my account statement"
   Expected: Recent transactions

4. "What loan options do I have?"
   Expected: Loan information
```

---

## Troubleshooting Deployment

### UI shows "Connection refused"
**Cause:** UI can't reach orchestrator
**Fix:**
1. Verify orchestrator URL is publicly accessible
2. Check `ORCHESTRATOR_URL` secret in Streamlit Cloud settings
3. Test orchestrator directly: `curl https://your-orchestrator-url/docs`

### Backend returns 502/503 errors
**Cause:** Backend service not running or unhealthy
**Fix:**
1. Check service logs in hosting dashboard
2. Verify Java 17+ is available
3. Ensure port 8081 is exposed
4. Check health endpoint: `/api/balance?accountId=123`

### CORS errors in browser console
**Cause:** Backend rejecting cross-origin requests
**Fix:**
1. Verify `@CrossOrigin(origins = "*")` is on `BankController`
2. For production, specify exact origins instead of `*`
3. Rebuild and redeploy backend

### Orchestrator import errors
**Cause:** Missing dependencies
**Fix:**
1. Ensure `requirements.txt` includes all packages
2. Check build logs for pip install errors
3. Verify Python 3.11+ is being used

---

## Cost Estimates (Monthly)

### Free Tier Setup
- **Backend:** Render free tier (750 hours/month)
- **Orchestrator:** Render free tier (750 hours/month)
- **UI:** Streamlit Cloud free tier (unlimited)
- **Total:** $0/month (with usage limits)

### Production Setup
- **Backend:** $7-25/month (Render/Railway)
- **Orchestrator:** $7-25/month (Render/Railway)
- **UI:** Free (Streamlit Cloud)
- **Database (if added):** $0-15/month
- **Total:** ~$15-65/month

---

## Security Considerations for Production

Before going to production, implement:

1. **Authentication:** Add JWT/OAuth to all services
2. **CORS:** Restrict origins to your UI domain only
3. **HTTPS:** Enable TLS on all endpoints
4. **Input validation:** Sanitize all user inputs
5. **Rate limiting:** Prevent abuse
6. **Database:** Replace in-memory storage with PostgreSQL/MongoDB
7. **Secrets management:** Use environment variables or secret managers
8. **Monitoring:** Add logging and error tracking (Sentry, DataDog)

---

## Next Steps

1. ✅ **Code is pushed to GitHub:** https://github.com/Dhanusankar/Banking
2. 🚀 **Choose deployment option** from above
3. 🧪 **Test all endpoints** after deployment
4. 📊 **Monitor logs** for errors
5. 🔒 **Implement security** before sharing publicly

---

## Support

- **Repository:** https://github.com/Dhanusankar/Banking
- **Issues:** Create an issue on GitHub
- **Documentation:** See README.md in repository

---

**Remember:** This is a POC. For production use, add proper authentication, database persistence, error handling, and security measures.
