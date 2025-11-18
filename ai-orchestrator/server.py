"""
FastAPI server exposing POST /chat. Uses the agent to generate an API call
description and executes the call against the backend, returning structured
responses and keeping in-memory chat history.
"""
from fastapi import FastAPI
from pydantic import BaseModel
import requests

from agent import build_api_call
from chat_history import add_message, get_history

app = FastAPI()


class ChatRequest(BaseModel):
    message: str


@app.post("/chat")
def chat(req: ChatRequest):
    add_message("user", req.message)
    api_call = build_api_call(req.message)

    if api_call.get("intent") == "fallback":
        reply = api_call.get("message", "Sorry, I don't understand.")
        add_message("assistant", reply)
        return {"reply": reply, "history": get_history()}

    if "error" in api_call:
        reply = api_call["error"]
        add_message("assistant", reply)
        return {"reply": reply, "history": get_history()}

    try:
        method = api_call.get("method", "GET").upper()
        url = api_call.get("url")
        if method == "GET":
            r = requests.get(url, params=api_call.get("params"), timeout=5)
        else:
            r = requests.post(url, json=api_call.get("json"), timeout=5)

        try:
            data = r.json()
        except Exception:
            data = {"text": r.text}

        reply = {"intent": api_call.get("intent"), "status_code": r.status_code, "data": data}
        add_message("assistant", str(reply))
        return {"reply": reply, "history": get_history()}

    except requests.RequestException as e:
        reply = f"Error calling backend: {e}"
        add_message("assistant", reply)
        return {"reply": reply, "history": get_history()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
