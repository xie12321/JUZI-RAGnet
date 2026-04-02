# session_store.py
from typing import Dict, Optional
from graph.state import AgentState

class SessionStore:
    def __init__(self):
        self._store: Dict[str, AgentState] = {}

    def get(self, session_id: str) -> Optional[AgentState]:
        return self._store.get(session_id)

    def set(self, session_id: str, state: AgentState):
        self._store[session_id] = state

    def delete(self, session_id: str):
        if session_id in self._store:
            del self._store[session_id]

session_store = SessionStore()