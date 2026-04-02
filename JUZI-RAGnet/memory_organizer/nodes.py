# memory_organizer/nodes.py
import time
from langchain_core.messages import HumanMessage

from memory_organizer.state import MemoryState
from model import llm
from logger_config import logger

def importance_node(state: MemoryState):
    """使用 LLM 判断每条消息是否重要，返回重要消息列表和剩余消息"""
    messages = state["messages"]
    important = []
    remaining = []
    for msg in messages:
        prompt = f"""请判断以下消息是否包含需要长期记住的重要信息（如用户个人信息、偏好、重要指令、关键事实等）。只回答“是”或“否”。

消息：{msg['content']}
"""
        response = llm.invoke([HumanMessage(content=prompt)])
        if "是" in response.content:
            important.append(msg["content"])
        else:
            remaining.append(msg)
    logger.bind(node="memory_importance").info(f"提取重要信息 {len(important)} 条")
    return {
        "important": important,
        "messages": remaining,
        "iteration": state.get("iteration", 0) + 1
    }

def summarize_node(state: MemoryState):
    """对剩余消息进行概括（使用 LLM）"""
    remaining = state["messages"]
    if not remaining:
        return {"summary": ""}
    # 将剩余消息拼接为文本
    text = "\n".join([f"{m['role']}: {m['content']}" for m in remaining])
    prompt = f"""请将以下对话概括为一段简短的文字（不超过 200 字），保留关键信息：
{text}
"""
    response = llm.invoke([HumanMessage(content=prompt)])
    summary = response.content.strip()
    logger.bind(node="memory_summarize").info(f"生成摘要 {len(summary)} 字")
    return {"summary": summary}

def should_continue(state: MemoryState) -> str:
    """
    判断是否需要继续迭代
    条件：
    - 剩余消息数量超过 10 条，且迭代次数小于 3，且本次提取到了重要信息 -> 继续重要性判断
    - 否则进入概括节点
    """
    remaining_count = len(state["messages"])
    iteration = state.get("iteration", 0)
    last_important = bool(state.get("important", []))
    if remaining_count > 10 and iteration < 3 and last_important:
        return "importance"
    else:
        return "summarize"