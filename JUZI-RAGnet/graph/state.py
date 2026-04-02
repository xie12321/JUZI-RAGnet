# graph/state.py
from typing import List, Optional, Dict, Any, Annotated, TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from config import MAX_ITERATIONS

class AgentState(TypedDict):
    user_input: str
    messages: Annotated[List[BaseMessage], add_messages]
    iteration: int
    plan: Optional[str]
    experiences: Optional[List[str]]
    tool_results: Optional[str]
    tool_results_dict: Optional[Dict[str, Any]]
    verification_passed: Optional[bool]
    verification_feedback: Optional[str]
    error_found: Optional[bool]
    final_answer: Optional[str]
    need_tool: Optional[bool]
    tool_suggestion: Optional[Dict[str, Any]]
    current_step: Optional[int]
    plan_valid: Optional[bool]
    plan_feedback: Optional[str]

def after_verification(state: AgentState):
    if state.get("verification_passed"):
        return "error_check"
    else:
        if state.get("iteration", 0) >= MAX_ITERATIONS:
            return "output"
        return "planning"

def after_error_check(state: AgentState):
    if state.get("error_found"):
        if state.get("iteration", 0) >= MAX_ITERATIONS:
            return "output"
        return "planning"
    else:
        return "output"