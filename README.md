# Banking AI POC

A complete Proof-of-Concept demonstrating AI-powered banking operations with:
- **Java Spring Boot Backend** - RESTful API for banking operations (balance, transfer, statement, loan)
- **Python AI Orchestrator** - FastAPI + LangGraph workflow for intent classification and API orchestration
- **Streamlit UI** - Interactive chat interface for natural language banking queries

## Architecture

```
Streamlit UI (Port 8501)
    ↓
AI Orchestrator FastAPI (Port 8000)
    ↓
Spring Boot Backend (Port 8081)
```

## Features

- ✅ Natural language processing for banking queries
- ✅ Intent classification (balance, transfer, statement, loan)
- ✅ Graph-based workflow orchestration with LangGraph
- ✅ RESTful API with CORS support
- ✅ Docker support for easy deployment
- ✅ Configurable orchestrator URL for cloud deployment

## Quick Start (Local Development)

### Prerequisites
- Java 17+
- Python 3.11+
- Maven 3.x

### 1. Start Backend
```powershell
cd backend-java/banking-backend
mvn spring-boot:run
```
Backend runs at: http://localhost:8081

### 2. Start AI Orchestrator
```powershell
cd ai-orchestrator
pip install -r requirements.txt
uvicorn server:app --reload --port 8000
```
Orchestrator runs at: http://localhost:8000

### 3. Start UI
```powershell
cd ui
pip install -r requirements.txt
streamlit run ui.py
```
UI opens at: http://localhost:8501

## Sample Prompts
- "What's my balance?"
- "Transfer 2000 to Kiran"
- "Show my account statement"
- "What loan options do I have?"

## Deployment Options

### Option 1: Docker Compose (Recommended)
```bash
docker-compose up --build
```
This starts all three services in containers with proper networking.

### Option 2: Streamlit Cloud (UI Only)
1. Push code to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Deploy from repository: `Dhanusankar/Banking`
4. Set main file path: `ui/ui.py`
5. Add secret: `ORCHESTRATOR_URL = "https://your-orchestrator-url/chat"`
6. Deploy backend and orchestrator separately (see below)

### Option 3: Individual Service Deployment

#### Backend (Render/Railway/Heroku)
```bash
cd backend-java/banking-backend
# Deploy using Dockerfile or Maven buildpack
```

#### Orchestrator (Render/Railway/Fly.io)
```bash
cd ai-orchestrator
# Deploy using Dockerfile
```

#### UI (Streamlit Cloud)
- Main file: `ui/ui.py`
- Python version: 3.11
- Secret: `ORCHESTRATOR_URL = "https://your-orchestrator-domain/chat"`

### Option 4: Expose Local Backend with ngrok
```powershell
# Install ngrok, then:
ngrok http 8000

# Copy the forwarding URL (e.g., https://abcd-1234.ngrok.io)
# Set in Streamlit app:
$env:ORCHESTRATOR_URL = 'https://abcd-1234.ngrok.io/chat'
streamlit run ui.py
```

## API Endpoints

### Backend (Spring Boot)
- `GET /api/balance?accountId=123` - Get account balance
- `POST /api/transfer` - Transfer money
  ```json
  {"fromAccount": "123", "toAccount": "kiran", "amount": 100}
  ```
- `GET /api/statement?accountId=123` - Get account statement
- `GET /api/loan?accountId=123` - Get loan information

### Orchestrator (FastAPI)
- `POST /chat` - Process natural language banking queries
  ```json
  {"message": "What's my balance?"}
  ```
- `GET /docs` - Interactive API documentation

## Configuration

### Backend Port
Edit `backend-java/banking-backend/src/main/resources/application.properties`:
```properties
server.port=8081
```

### Orchestrator URL (UI)
Three ways to configure (priority order):
1. Streamlit secrets: Add `ORCHESTRATOR_URL` in `.streamlit/secrets.toml`
2. Environment variable: `$env:ORCHESTRATOR_URL = "http://..."`
3. Default: `http://localhost:8000/chat`

## Project Structure

```
banking-ai-poc/
├── backend-java/
│   └── banking-backend/
│       ├── src/main/java/com/banking/
│       │   ├── controller/     # REST controllers
│       │   ├── service/        # Business logic
│       │   ├── model/          # Data models
│       │   └── dto/            # Data transfer objects
│       ├── pom.xml
│       └── Dockerfile
├── ai-orchestrator/
│   ├── agent.py               # LangGraph workflow
│   ├── server.py              # FastAPI app
│   ├── intent_classifier.py   # Rule-based NLP
│   ├── transfer_extractor.py  # Extract transfer details
│   ├── chat_history.py        # In-memory history
│   ├── requirements.txt
│   └── Dockerfile
├── ui/
│   ├── ui.py                  # Streamlit chat interface
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .streamlit/
│       ├── config.toml
│       └── secrets.toml.example
├── docker-compose.yml
├── .gitignore
└── README.md
```

## Technology Stack

- **Backend**: Java 17, Spring Boot 3.x, Maven
- **Orchestrator**: Python 3.11, FastAPI, LangGraph, Uvicorn
- **UI**: Streamlit, Requests
- **Deployment**: Docker, Docker Compose

## Important Notes

### GitHub Pages Limitation
⚠️ **GitHub Pages cannot host this application** because:
- GitHub Pages only serves static HTML/CSS/JS files
- This POC requires backend services (Java Spring Boot, Python FastAPI)
- Use alternatives: Streamlit Cloud, Render, Railway, Heroku, or Docker deployment

### Security Notice
🔒 This is a POC with:
- In-memory data (no persistence)
- CORS enabled for all origins (`*`)
- No authentication/authorization
- Hardcoded account IDs

For production, implement:
- Database persistence
- Restricted CORS origins
- JWT/OAuth authentication
- Input validation and sanitization
- HTTPS/TLS encryption

## Troubleshooting

### Backend won't start
- Ensure Java 17+ is installed: `java -version`
- Check port 8081 is free: `netstat -an | findstr 8081`
- Verify Maven build: `mvn clean package`

### Orchestrator errors
- Install dependencies: `pip install -r requirements.txt`
- Check Python version: `python --version` (3.11+ required)
- Verify server: `curl http://localhost:8000/docs`

### UI can't connect
- Ensure orchestrator is running on port 8000
- Check `ORCHESTRATOR_URL` configuration
- For cloud deployment, verify backend URL is publicly accessible

### Connection refused errors
- Local: Start backend (8081) → orchestrator (8000) → UI (8501) in order
- Cloud: Ensure orchestrator URL is publicly reachable
- Docker: Use service names (e.g., `http://orchestrator:8000/chat`)

## License

This is a Proof-of-Concept project for demonstration purposes.

## Contributing

This is a POC repository. For improvements:
1. Fork the repository
2. Create a feature branch
3. Submit a pull request

## Contact

Repository: [Dhanusankar/Banking](https://github.com/Dhanusankar/Banking)
