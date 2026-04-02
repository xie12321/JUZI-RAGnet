import json
import time
from typing import List
from langchain_core.messages import HumanMessage, AIMessage
from langchain.tools import StructuredTool
from pydantic import BaseModel, Field

from model import llm, structured_llm, verification_structured_llm, Plan
from memory import reasoning_kb, experience_kb, memory_kb
from tools import web_search_func, recall_memory_func
from logger_config import logger

# ---------- 定义工具 ----------
class WebSearchInput(BaseModel):
    query: str = Field(description="搜索关键词")
    max_results: int = Field(default=5, description="返回结果数量")

class RecallMemoryInput(BaseModel):
    query: str = Field(description="需要回忆的内容")
    k: int = Field(default=2, description="返回记忆条数")

web_search_tool = StructuredTool.from_function(
    func=web_search_func,
    name="web_search",
    description="通过互联网搜索实时信息，返回摘要和来源。",
    args_schema=WebSearchInput,
)

recall_memory_tool = StructuredTool.from_function(
    func=recall_memory_func,
    name="recall_long_term_memory",
    description="从长期记忆中检索与当前问题相关的过往对话，支持按类别过滤。",
    args_schema=RecallMemoryInput,
)

all_tools = [web_search_tool, recall_memory_tool]

# ---------- 节点函数 ----------
def planning_node(state):
    start_time = time.time()
    user_input = state["user_input"]

    # 从推理库检索理论知识
    theory_docs = reasoning_kb.similarity_search(user_input, k=3)
    theory = "\n".join([doc.page_content for doc in theory_docs])

    # ---------- 新增：获取短期记忆（对话历史） ----------
    messages = state.get("messages", [])
    # 取最近 8 条消息，避免上下文过长
    recent_messages = messages[-8:]
    history_lines = []
    for msg in recent_messages:
        if isinstance(msg, HumanMessage):
            history_lines.append(f"用户：{msg.content}")
        elif isinstance(msg, AIMessage):
            history_lines.append(f"AI：{msg.content}")
    history_text = "\n".join(history_lines) if history_lines else "（无历史）"
    # -----------------------------------------------

    # 如果有上次验证失败的反馈，加入提示词
    feedback = state.get("plan_feedback", "")
    feedback_note = f"\n上一次生成的计划无效，错误信息：{feedback}。请修正后重新生成。" if feedback else ""

    prompt = f"""你是规划专家。用户需求：{user_input}
对话历史（最近对话）：
{history_text}
理论知识（从推理库获取）：
{theory}
{feedback_note}
请生成一个详细的执行计划，包括需要调用的工具、参数、步骤。
可用工具：{', '.join([t.name for t in all_tools])}
每个步骤可包含 `depends_on` 字段，用于指定参数值来自前一步的输出。
例如，如果第一步返回的 JSON 包含 `temperature` 字段，第二步可以使用 `"depends_on": {{"temperature": "step_0.temperature"}}`。
输出符合结构的计划。
"""
    plan_obj = structured_llm.invoke([HumanMessage(content=prompt)])
    plan_json = plan_obj.model_dump_json()
    elapsed = (time.time() - start_time) * 1000
    logger.bind(node="planning", user_input=user_input, plan=plan_obj.model_dump(), elapsed_ms=elapsed, llm_calls=1).info("Planning completed")
    return {
        "plan": plan_json,
        "iteration": state.get("iteration", 0) + 1,
        "tool_results_dict": {},
        "need_tool": False,
        "tool_suggestion": None,
        "current_step": 0,
        "plan_valid": None,
        "plan_feedback": None,
        "prepared_params": None,
    }

def should_use_tools_node(state):
    user_input = state["user_input"].lower()
    no_tool_keywords = ["你好", "hi", "hello", "再见", "谢谢", "哈哈", "呵呵", "哦", "嗯"]
    if any(kw in user_input for kw in no_tool_keywords):
        return {"need_tools": False}
    return {"need_tools": True}

def prepare_tools_node(state):
    """工具调用准备：解析依赖，填充参数（不执行）"""
    plan_str = state.get("plan", "{}")
    try:
        plan = Plan.model_validate_json(plan_str)
    except Exception as e:
        logger.warning(f"解析计划失败: {e}")
        plan = Plan(steps=[])

    current_step = state.get("current_step", 0)
    if current_step >= len(plan.steps):
        # 无工具步骤，直接返回
        return {"need_tool": False, "tool_suggestion": None, "prepared_params": None}

    step = plan.steps[current_step]
    params = step.params.copy()
    results_dict = state.get("tool_results_dict", {})

    # 解析依赖
    if step.depends_on:
        for param_name, source in step.depends_on.items():
            try:
                # 解析 source 格式：step_X.field 或 tool_name.field
                if source.startswith("step_"):
                    step_idx = int(source.split("_")[1].split(".")[0])
                    field = source.split(".")[1] if "." in source else None
                    result_obj = results_dict.get(f"step_{step_idx}")
                else:
                    tool_name = source.split(".")[0]
                    field = source.split(".")[1] if "." in source else None
                    # 查找最近一次使用该工具的结果
                    result_obj = None
                    for key, val in results_dict.items():
                        if key.endswith(f"_{tool_name}"):
                            result_obj = val
                            break
                if result_obj is not None:
                    if isinstance(result_obj, str):
                        try:
                            result_obj = json.loads(result_obj)
                        except:
                            pass
                    if field is not None:
                        parts = field.split(".")
                        value = result_obj
                        for part in parts:
                            if isinstance(value, dict):
                                value = value.get(part)
                            else:
                                value = None
                                break
                        if value is not None:
                            params[param_name] = value
                    else:
                        params[param_name] = result_obj
            except Exception as e:
                logger.warning(f"解析依赖 {source} 失败: {e}")

    # 存储准备好的参数
    return {
        "prepared_params": params,
        "need_tool": True,
        "current_step": current_step,
        "tool_suggestion": {
            "tool": step.tool,
            "params": params,
            "step_index": current_step,
            "total_steps": len(plan.steps)
        }
    }

def plan_validator_node(state):
    """规划验证器：验证填充后的参数是否合法，也处理空计划"""
    # 如果没有计划（不需要工具的情况），直接通过
    if not state.get("plan") or state.get("plan") == "{}":
        return {"plan_valid": True, "plan_feedback": None}

    prepared_params = state.get("prepared_params")
    tool_suggestion = state.get("tool_suggestion")
    if not prepared_params or not tool_suggestion:
        return {"plan_valid": False, "plan_feedback": "计划参数未准备"}

    # 检查参数是否完整（非空）
    missing = [k for k, v in prepared_params.items() if v is None or v == ""]
    if missing:
        return {"plan_valid": False, "plan_feedback": f"参数缺失: {', '.join(missing)}"}

    # 可选：根据工具定义检查参数类型（这里简化）
    return {"plan_valid": True, "plan_feedback": None}

def experience_retrieval_node(state):
    """经验库：检索成功经验（供输出节点参考）"""
    plan = state.get("plan", "")
    experiences = []   # 初始化空列表
    if plan:
        try:
            docs = experience_kb.similarity_search(plan, k=2, filter={"type": "success"})
            experiences = [doc.page_content for doc in docs if doc.page_content.strip()]
        except Exception as e:
            logger.warning(f"经验检索失败: {e}")
    return {"experiences": experiences}

def execute_tools_node(state):
    """执行工具：根据准备好的参数调用工具"""
    tool_suggestion = state.get("tool_suggestion")
    if not tool_suggestion:
        return {"need_tool": False, "tool_results": "无工具可执行"}

    step_index = tool_suggestion["step_index"]
    tool_name = tool_suggestion["tool"]
    params = tool_suggestion["params"]

    tool_map = {t.name: t for t in all_tools}
    tool = tool_map.get(tool_name)
    if tool:
        try:
            res = tool.invoke(params)
            results_dict = state.get("tool_results_dict", {})
            results_dict[f"step_{step_index}_{tool_name}"] = res
            tool_results_str = f"工具 {tool_name} 返回：{res}"
            return {
                "need_tool": False,
                "tool_results": tool_results_str,
                "tool_results_dict": results_dict,
                "current_step": step_index + 1,
                "tool_suggestion": None,
                "prepared_params": None
            }
        except Exception as e:
            error_msg = f"执行工具失败: {e}"
            logger.error(error_msg)
            return {
                "need_tool": False,
                "tool_results": error_msg,
                "tool_results_dict": state.get("tool_results_dict", {}),
                "current_step": step_index + 1,
                "tool_suggestion": None,
                "prepared_params": None
            }
    else:
        error_msg = f"未知工具 {tool_name}"
        logger.warning(error_msg)
        return {
            "need_tool": False,
            "tool_results": error_msg,
            "tool_results_dict": state.get("tool_results_dict", {}),
            "current_step": step_index + 1,
            "tool_suggestion": None,
            "prepared_params": None
        }

def verification_node(state):
    """结果验证节点：验证工具返回结果是否合理"""
    start = time.time()
    user_input = state["user_input"]
    results = state.get("tool_results", "")
    docs = reasoning_kb.similarity_search("验证结果合理性", k=3)
    rules = "\n".join([doc.page_content for doc in docs])

    prompt = f"""你是验证专家。用户需求：{user_input}
工具执行结果：{results}
验证规则（从推理库获取）：
{rules}

请判断结果是否合理、是否满足用户需求。输出符合结构的验证结果。
"""
    ver_obj = verification_structured_llm.invoke([HumanMessage(content=prompt)])
    elapsed = (time.time() - start) * 1000
    logger.bind(node="verify", user_input=user_input, passed=ver_obj.passed, elapsed_ms=elapsed, llm_calls=1).info("Verification completed")
    return {
        "verification_passed": ver_obj.passed,
        "verification_feedback": ver_obj.feedback
    }

def error_check_node(state):
    """错误检查节点：结合经验库和用户需求比对"""
    start = time.time()
    user_input = state["user_input"]
    results = state.get("tool_results", "")
    max_len = 500
    if len(results) > max_len:
        results = results[:max_len] + "..."

    error_found = False
    error_info = ""

    # 从经验库检索错误模式
    try:
        error_docs = experience_kb.similarity_search(results, k=1, filter={"type": "error"})
        if error_docs and error_docs[0].page_content.strip():
            content = error_docs[0].page_content
            if "错误" in content or "bug" in content or "不对" in content:
                error_found = True
                error_info = content
    except Exception as e:
        logger.warning(f"错误检查检索失败: {e}")

    # 用 LLM 比对用户需求是否满足
    try:
        prompt = f"""请判断以下工具执行结果是否满足了用户的原始需求。
用户需求：{user_input}
工具执行结果：{results}
请只回答 "是" 或 "否"。
"""
        response = llm.invoke([HumanMessage(content=prompt)])
        satisfied = response.content.strip().lower() == "是"
        if not satisfied:
            error_found = True
            error_info += f"；用户需求未满足：{response.content}"
    except Exception as e:
        logger.warning(f"用户需求比对失败: {e}")

    elapsed = (time.time() - start) * 1000
    logger.bind(node="error_check", error_found=error_found, error_info=error_info, elapsed_ms=elapsed, llm_calls=1).info("Error check completed")
    return {"error_found": error_found, "error_info": error_info}

def output_node(state):
    start = time.time()
    results = state.get("tool_results", "")
    experiences = state.get("experiences", [])
    if not isinstance(experiences, list):
        experiences = []
    exp_str = "\n".join([f"- {e}" for e in experiences[:2]])

    # ---------- 新增：从状态中获取短期记忆 ----------
    messages = state.get("messages", [])
    # 取最近 10 条消息，避免过长
    recent_messages = messages[-10:]
    history_lines = []
    for msg in recent_messages:
        if isinstance(msg, HumanMessage):
            history_lines.append(f"用户：{msg.content}")
        elif isinstance(msg, AIMessage):
            history_lines.append(f"AI：{msg.content}")
    history_text = "\n".join(history_lines) if history_lines else "（无历史）"
    # ------------------------------------------

    prompt = f"""用户需求：{state["user_input"]}
对话历史：
{history_text}
工具执行结果：{results}
参考经验：
{exp_str}

请生成最终回答给用户，要友好、自然。
"""
    response = llm.invoke([HumanMessage(content=prompt)])
    final_answer = response.content
    elapsed = (time.time() - start) * 1000
    logger.bind(node="output", final_answer=final_answer[:200], elapsed_ms=elapsed, llm_calls=1).info("Output generated")
    return {"final_answer": final_answer, "messages": [AIMessage(content=final_answer)]}