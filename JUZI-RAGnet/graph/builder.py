from langgraph.graph import StateGraph, END
from graph.state import AgentState, after_verification, after_error_check
from graph.nodes import (
    planning_node, should_use_tools_node, prepare_tools_node, plan_validator_node,
    experience_retrieval_node, execute_tools_node, verification_node,
    error_check_node, output_node
)
from config import MAX_ITERATIONS
from model import Plan

def build_graph():
    workflow = StateGraph(AgentState)

    workflow.add_node("should_use_tools", should_use_tools_node)
    workflow.add_node("planning", planning_node)
    workflow.add_node("prepare_tools", prepare_tools_node)
    workflow.add_node("plan_validator", plan_validator_node)
    workflow.add_node("experience", experience_retrieval_node)
    workflow.add_node("execute_tools", execute_tools_node)
    workflow.add_node("verify", verification_node)
    workflow.add_node("error_check", error_check_node)
    workflow.add_node("output", output_node)

    workflow.set_entry_point("should_use_tools")

    def after_should_use_tools(state):
        if state.get("need_tools", True):
            return "planning"
        else:
            return "plan_validator"   # 不需要工具，直接验证空计划

    workflow.add_conditional_edges("should_use_tools", after_should_use_tools, {
        "planning": "planning",
        "plan_validator": "plan_validator"
    })

    workflow.add_edge("planning", "prepare_tools")
    workflow.add_edge("prepare_tools", "plan_validator")

    def after_plan_validator(state):
        if state.get("plan_valid"):
            return "experience"
        else:
            if state.get("iteration", 0) >= MAX_ITERATIONS:
                return "output"
            return "should_use_tools"   # 重新从判断节点开始

    workflow.add_conditional_edges("plan_validator", after_plan_validator, {
        "experience": "experience",
        "should_use_tools": "should_use_tools",
        "output": "output"
    })

    def after_experience(state):
        plan_str = state.get("plan", "{}")
        current_step = state.get("current_step", 0)
        try:
            plan = Plan.model_validate_json(plan_str)
            has_steps = current_step < len(plan.steps)
        except:
            has_steps = False

        if has_steps:
            return "execute_tools"
        else:
            return "output"

    workflow.add_conditional_edges("experience", after_experience, {
        "execute_tools": "execute_tools",
        "output": "output"
    })

    workflow.add_edge("execute_tools", "verify")
    workflow.add_conditional_edges("verify", after_verification, {
        "error_check": "error_check",
        "should_use_tools": "should_use_tools",
        "output": "output"
    })
    workflow.add_conditional_edges("error_check", after_error_check, {
        "should_use_tools": "should_use_tools",
        "output": "output"
    })
    workflow.add_edge("output", END)

    return workflow.compile()