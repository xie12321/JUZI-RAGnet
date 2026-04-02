# api.py
import json
import uuid
import time
import asyncio
from typing import Optional, Dict, Any
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv

from session_store import session_store
from graph.builder import build_graph
from graph.state import AgentState
from memory import memory_kb, experience_kb, reasoning_kb
from mid_term_memory import MidTermMemory
from logger_config import logger
from model import Plan

load_dotenv()

app = FastAPI(title="Model Enhancer API", description="OpenAI-compatible reasoning and memory enhancement")

# ---------- OpenAI 兼容的请求/响应模型 ----------
class ChatMessage(BaseModel):
    role: str
    content: Optional[str] = None
    tool_calls: Optional[list] = None
    tool_call_id: Optional[str] = None

class ChatCompletionRequest(BaseModel):
    model: str
    messages: list[ChatMessage]
    stream: bool = False
    tools: Optional[list] = None
    tool_choice: Optional[str] = "auto"

class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: list
    usage: dict = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

# ---------- 辅助函数 ----------
def convert_messages_to_state(messages: list[ChatMessage]) -> AgentState:
    # 提取最后一条用户消息
    user_input = None
    for msg in reversed(messages):
        if msg.role == "user":
            user_input = msg.content
            break
    if not user_input:
        user_input = ""
    return AgentState(
        user_input=user_input,
        messages=[],
        iteration=0,
        plan=None,
        experiences=None,
        tool_results=None,
        tool_results_dict=None,
        verification_passed=None,
        verification_feedback=None,
        error_found=None,
        final_answer=None,
        need_tool=False,
        tool_suggestion=None,
        current_step=0,
        plan_valid=None,
        plan_feedback=None,
    )

def run_enhancer(state: AgentState):
    """运行图，返回最终状态（可能中断）"""
    graph = build_graph()
    final_state = None
    for step in graph.stream(state):
        for node_name, node_output in step.items():
            final_state = node_output
    return final_state

# ---------- API 端点 ----------
@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    session_id = str(uuid.uuid4())
    request_id = str(uuid.uuid4())
    start_time = time.time()

    logger.bind(request_id=request_id).info("Request started", request=request.dict())

    # 获取或创建会话状态
    saved_state = session_store.get(session_id)
    if saved_state:
        state = saved_state
    else:
        state = convert_messages_to_state(request.messages)
        # 加载中期记忆
        mid_mem = MidTermMemory()
        # 注意：中期记忆与短期记忆的融合需要额外处理，这里简化，仅演示
        # 实际可将 mid_mem 的内容合并到 state 的 messages 中

    # 运行增强器
    final_state = run_enhancer(state)

    # 判断是否需要外部工具
    if final_state.get("need_tool"):
        # 保存状态以便后续继续
        session_store.set(session_id, final_state)
        suggestion = final_state["tool_suggestion"]
        tool_call_id = f"call_{uuid.uuid4().hex[:8]}"
        response_message = {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": tool_call_id,
                    "type": "function",
                    "function": {
                        "name": suggestion["tool"],
                        "arguments": json.dumps(suggestion["params"])
                    }
                }
            ]
        }
        elapsed = (time.time() - start_time) * 1000
        logger.bind(request_id=request_id, session_id=session_id, elapsed_ms=elapsed).info("Request completed with tool_calls")
        return ChatCompletionResponse(
            id=f"chatcmpl-{uuid.uuid4().hex}",
            created=int(time.time()),
            model=request.model,
            choices=[{"index": 0, "message": response_message, "finish_reason": "tool_calls"}],
        )
    else:
        final_answer = final_state.get("final_answer", "")
        # 存储成功经验
        plan_str = final_state.get("plan")
        if plan_str and final_state.get("verification_passed"):
            try:
                plan_obj = Plan.model_validate_json(plan_str)
                if len(plan_obj.steps) > 1:
                    experience_text = f"## 任务：{final_state['user_input']}\n### 执行计划：\n{plan_obj.model_dump_json(indent=2)}\n### 结果：\n{final_answer}"
                    experience_kb.add_texts([experience_text], metadatas=[{"type": "success", "timestamp": time.time()}])
                    logger.info("Success experience stored")
            except Exception as e:
                logger.warning(f"存储经验失败: {e}")
        session_store.delete(session_id)
        elapsed = (time.time() - start_time) * 1000
        logger.bind(request_id=request_id, session_id=session_id, elapsed_ms=elapsed).info("Request completed with final answer")
        return ChatCompletionResponse(
            id=f"chatcmpl-{uuid.uuid4().hex}",
            created=int(time.time()),
            model=request.model,
            choices=[{"index": 0, "message": {"role": "assistant", "content": final_answer}, "finish_reason": "stop"}],
        )

@app.post("/v1/tool_results")
async def submit_tool_results(session_id: str, tool_results: Dict[str, Any]):
    request_id = str(uuid.uuid4())
    logger.bind(request_id=request_id).info("Tool results submitted", session_id=session_id)
    saved_state = session_store.get(session_id)
    if not saved_state:
        raise HTTPException(status_code=404, detail="Session not found")
    # 将工具结果注入状态
    tool_results_dict = saved_state.get("tool_results_dict", {})
    tool_results_dict.update(tool_results)
    saved_state["tool_results_dict"] = tool_results_dict
    tool_results_str = "\n".join([f"{k}: {v}" for k, v in tool_results.items()])
    saved_state["tool_results"] = (saved_state.get("tool_results", "") + "\n" + tool_results_str).strip()
    saved_state["current_step"] = saved_state.get("current_step", 0) + 1
    # 继续运行增强器
    final_state = run_enhancer(saved_state)
    if final_state.get("need_tool"):
        session_store.set(session_id, final_state)
        suggestion = final_state["tool_suggestion"]
        tool_call_id = f"call_{uuid.uuid4().hex[:8]}"
        response_message = {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": tool_call_id,
                    "type": "function",
                    "function": {
                        "name": suggestion["tool"],
                        "arguments": json.dumps(suggestion["params"])
                    }
                }
            ]
        }
        return {
            "id": f"chatcmpl-{uuid.uuid4().hex}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": "enhancer",
            "choices": [{"index": 0, "message": response_message, "finish_reason": "tool_calls"}],
        }
    else:
        final_answer = final_state.get("final_answer", "")
        session_store.delete(session_id)
        return {
            "id": f"chatcmpl-{uuid.uuid4().hex}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": "enhancer",
            "choices": [{"index": 0, "message": {"role": "assistant", "content": final_answer}, "finish_reason": "stop"}],
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)