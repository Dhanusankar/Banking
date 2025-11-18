"""In-memory chat history for the orchestrator (POC)."""
from typing import List, Dict

history: List[Dict] = []


def add_message(role: str, message: str):
    history.append({"role": role, "message": message})


def get_history() -> List[Dict]:
    return history
