# Render.com Deployment Notes

## ⚠️ Llama-3 Integration Limitation

### Current System Features:
- ✅ **6-Node LangGraph Workflow** (implemented)
- ✅ **LLM-powered Intent Classification** via Llama-3 (local only)
- ✅ **Confidence-based Routing** (threshold: 0.80)
- ✅ **HIL for Low Confidence** requests
- ✅ **Automatic Entity Extraction**
- ✅ **Fallback to Rule-based** classification

### Render.com Constraints:
1. **No Ollama Service**: Render doesn't provide Ollama runtime
2. **No GPU**: Free tier lacks GPU for LLM inference
3. **Memory Limits**: Free tier (512MB) insufficient for Llama-3 (needs 4-8GB)
4. **No Local Model Storage**: Can't store 4.7GB model file

### Deployment Options:

#### Option 1: Deploy with Rule-based Fallback (Recommended for Demo)
**What works:**
- All 6 workflow nodes operational
- HIL for high-value transfers ($5000+)
- Balance, transfer, statement, loan features
- Session management and checkpointing

**What doesn't work:**
- LLM confidence scoring (always uses fallback)
- Advanced NLU (typo handling via regex only)
- Low-confidence HIL triggers (only amount-based HIL)

**Deploy command:**
```bash
git add .
git commit -m "chore: Increase timeouts for production"
git push origin master
```

Then use Render dashboard to redeploy services.

#### Option 2: Hybrid Cloud Architecture (Production Ready)
Replace Ollama with **cloud-hosted LLM API**:

**Options:**
1. **OpenAI API** (GPT-4 Turbo) - $0.01/1K tokens
2. **Anthropic Claude** - $0.015/1K tokens  
3. **Google Gemini** - $0.0005/1K tokens (cheapest)
4. **Groq** - Free tier with Llama-3 (fastest)

**Implementation** (modify `llm_classifier.py`):
```python
# Replace Ollama endpoint
if os.environ.get("USE_CLOUD_LLM"):
    OLLAMA_API_URL = os.environ.get("LLM_API_URL", "https://api.groq.com/openai/v1/chat/completions")
    API_KEY = os.environ.get("LLM_API_KEY")
```

**Render Environment Variables:**
```yaml
envVars:
  - key: USE_CLOUD_LLM
    value: true
  - key: LLM_API_URL
    value: https://api.groq.com/openai/v1/chat/completions
  - key: LLM_API_KEY
    sync: false  # Set manually in Render dashboard
```

#### Option 3: Self-Hosted Ollama on VPS
Run Ollama on separate VPS (DigitalOcean, AWS EC2, etc.):
- **Cost**: ~$12-24/month (2-4GB RAM instance)
- **Setup**: Install Ollama, expose API via HTTPS
- **Update**: Set `OLLAMA_API_URL` env var to VPS URL

### Current Deployment Status:

**Local Development:**
- ✅ Full Llama-3 integration working
- ✅ All 6 nodes tested
- ✅ Confidence-based routing operational
- ✅ Backend: http://localhost:8081
- ✅ Orchestrator: http://localhost:8000  
- ✅ UI: http://localhost:8501

**Render.com (Previous Deploy):**
- ✅ Backend: https://banking-backend-*.onrender.com
- ⏳ Orchestrator: Uses rule-based fallback (no LLM)
- ⏳ UI: Functional but no LLM features

### Recommended Next Steps:

1. **For Demo/POC**: Deploy as-is with rule-based fallback
   - System works, just no LLM confidence scoring
   - Still has amount-based HIL ($5000+)
   
2. **For Production**: Integrate Groq API (free tier)
   - Modify `llm_classifier.py` for Groq
   - Add API key to Render env vars
   - Full LLM features in cloud

3. **For Enterprise**: Deploy Ollama on dedicated server
   - Full control over model
   - No API costs
   - Better privacy

### Files Modified (Ready to Commit):
- ✅ `ai-orchestrator/llm_classifier.py` - Timeout 30s → 60s
- ✅ `ui/ui_v2.py` - Timeout 10s → 60s
- 📝 Database files (auto-generated, don't commit)

### Commit & Redeploy:
```bash
cd C:\Users\dhanu\bank_ai\banking-ai-poc

# Commit timeout changes
git add ai-orchestrator/llm_classifier.py ui/ui_v2.py
git commit -m "chore: Increase API timeouts to 60s for LLM processing"
git push origin master

# Render will auto-deploy if connected to GitHub
# Or manually trigger via Render dashboard
```

### Testing After Deployment:
1. Check backend health: `https://your-backend.onrender.com/api/balance?accountId=123`
2. Test orchestrator: Send POST to `/chat` endpoint
3. Open UI and test: "What is my balance?"
4. Verify HIL: "Transfer 10000 to Kiran"

---

**Summary**: Your 6-node workflow is **complete and functional locally**. For Render deployment, system falls back to rule-based classification (no LLM confidence). To get full LLM features in cloud, integrate Groq or OpenAI API instead of local Ollama.
