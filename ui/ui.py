"""
Streamlit chat UI that sends messages to the AI Orchestrator (`/chat`) and
shows responses. Clean, minimal layout for the POC.
Run with: `streamlit run ui.py`
"""
import os
import streamlit as st
import requests

# Determine orchestrator URL from Streamlit secrets, environment, or fallback to localhost.
# When deploying to Streamlit Cloud, set the secret `ORCHESTRATOR_URL` to your backend URL
# (for example, https://my-backend.example.com). The app will prefer `st.secrets`, then
# the `ORCHESTRATOR_URL` env var, then `http://localhost:8000/chat` for local development.
API_URL = None
try:
    API_URL = st.secrets.get("ORCHESTRATOR_URL")
except Exception:
    API_URL = None

if not API_URL:
    API_URL = os.environ.get("ORCHESTRATOR_URL")

if not API_URL:
    API_URL = "http://localhost:8000/chat"


def send_message(message: str):
    """Send message to orchestrator and return response JSON."""
    try:
        r = requests.post(API_URL, json={"message": message}, timeout=10)
        return r.json()
    except Exception as e:
        return {"reply": f"Error: {e}"}


def main():
    st.set_page_config(page_title="Banking AI POC", layout="centered")
    st.title("Banking AI — Chat")

    if "messages" not in st.session_state:
        st.session_state["messages"] = []

    with st.form(key="msg_form", clear_on_submit=True):
        user_input = st.text_input("You", placeholder="Ask: What's my balance? Or Transfer 2000 to Kiran.")
        submitted = st.form_submit_button("Send")

    if submitted and user_input:
        st.session_state["messages"].append({"role": "user", "text": user_input})
        response = send_message(user_input)
        reply = response.get("reply")
        st.session_state["messages"].append({"role": "assistant", "text": str(reply)})

    # Display messages
    for msg in st.session_state["messages"]:
        if msg["role"] == "user":
            st.write(f"**You:** {msg['text']}")
        else:
            st.info(f"Assistant: {msg['text']}")


if __name__ == "__main__":
    main()
