# memory_organizer/builder.py
from langgraph.graph import StateGraph, END
from .state import MemoryState
from .nodes import importance_node, summarize_node, should_continue

def build_memory_organizer():
    workflow = StateGraph(MemoryState)

    workflow.add_node("importance", importance_node)
    workflow.add_node("summarize", summarize_node)

    workflow.set_entry_point("importance")
    workflow.add_conditional_edges("importance", should_continue, {
        "importance": "importance",
        "summarize": "summarize"
    })
    workflow.add_edge("summarize", END)

    return workflow.compile()