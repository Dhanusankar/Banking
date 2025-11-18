# Banking AI POC

This repository contains a Proof-of-Concept integrating a Spring Boot backend, a Python AI Orchestrator (FastAPI), and a Streamlit UI chat interface.

## Architecture

Streamlit UI <--> AI Orchestrator (FastAPI) --REST--> Spring Boot Backend

## Modules
- `backend-java/banking-backend` : Java Spring Boot service exposing `GET /api/balance` and `POST /api/transfer` using in-memory data.
- `ai-orchestrator` : FastAPI server with a small LangGraph-style agent that converts NL to intents and calls backend APIs.
- `ui` : Streamlit chat UI that communicates with the AI Orchestrator.

## How to Run

### 1. Spring Boot Backend
```powershell
cd backend-java/banking-backend
mvn spring-boot:run
```

### 2. AI Orchestrator (FastAPI)
```powershell
cd ai-orchestrator
python -m pip install -r requirements.txt
uvicorn server:app --reload --port 8000
```

### 3. Streamlit UI
```powershell
cd ui
python -m pip install -r requirements.txt
streamlit run ui.py
```

## Sample Prompts
- "What's my balance?"
- "Transfer 2000 to Kiran."

## Notes
- Backend default port: `8080`.
- AI Orchestrator default port: `8000`.
- This is a POC: there is no persistence, accounts are in-memory and reset on restart.
