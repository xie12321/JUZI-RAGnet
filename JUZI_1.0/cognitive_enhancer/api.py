import json
import os
import time
import uuid
import asyncio
from typing import List, Dict, Optional, AsyncGenerator

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, field_validator

from controller import run_self_reflection, run_self_reflection_stages
from wiki_reader import build_index
from logger_config import logger
from wiki_retriever import get_retriever
from response_parser import parse_openai_response
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI

app = FastAPI(title="Cognitive Enhancer API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- OpenAI 兼容请求/响应模型 ----------
class ChatMessage(BaseModel):
    role: str
    content: Optional[str] = ""
    tool_calls: Optional[List[Dict]] = None
    tool_call_id: Optional[str] = None

    @field_validator('content', mode='before')
    @classmethod
    def validate_content(cls, v):
        return v if v is not None else ""

class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    temperature: Optional[float] = 0.7
    stream: bool = False
    tools: Optional[List[Dict]] = None
    tool_choice: Optional[str] = "auto"
    api_base: Optional[str] = None
    api_key: Optional[str] = None
    ollama_base_url: Optional[str] = None

class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[Dict]
    usage: Dict = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

# ---------- 辅助函数 ----------
def format_messages_to_json(messages: List[ChatMessage]) -> str:
    return json.dumps([msg.dict() for msg in messages], ensure_ascii=False)

def create_stream_chunk(
    chunk_id: str,
    created: int,
    model: str,
    delta: Dict,
    finish_reason: Optional[str] = None
) -> str:
    chunk = {
        "id": chunk_id,
        "object": "chat.completion.chunk",
        "created": created,
        "model": model,
        "choices": [{"index": 0, "delta": delta, "finish_reason": finish_reason}]
    }
    return f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"

async def generate_stream_response(
    content: str,
    tool_calls: List[Dict],
    model: str,
    chunk_id: str,
    created: int
) -> AsyncGenerator[str, None]:
    """生成最终答案的 SSE 流式事件（不包含思考过程）"""
    yield create_stream_chunk(chunk_id, created, model, {"role": "assistant"})
    if tool_calls:
        for idx, tc in enumerate(tool_calls):
            delta_start = {
                "tool_calls": [{
                    "index": idx,
                    "id": f"call_{uuid.uuid4().hex[:8]}",
                    "type": "function",
                    "function": {"name": tc["name"], "arguments": ""}
                }]
            }
            yield create_stream_chunk(chunk_id, created, model, delta_start)
            arguments_str = json.dumps(tc["arguments"], ensure_ascii=False)
            chunk_size = 5
            for i in range(0, len(arguments_str), chunk_size):
                arguments_chunk = arguments_str[i:i+chunk_size]
                delta_args = {
                    "tool_calls": [{
                        "index": idx,
                        "function": {"arguments": arguments_chunk}
                    }]
                }
                yield create_stream_chunk(chunk_id, created, model, delta_args)
                await asyncio.sleep(0.01)
    if content:
        chunk_size = 10
        for i in range(0, len(content), chunk_size):
            content_chunk = content[i:i+chunk_size]
            delta_content = {"content": content_chunk}
            yield create_stream_chunk(chunk_id, created, model, delta_content)
            await asyncio.sleep(0.01)
    yield create_stream_chunk(chunk_id, created, model, {}, finish_reason="stop")
    yield "data: [DONE]\n\n"

def get_llm(request: ChatCompletionRequest):
    if request.api_base:
        return ChatOpenAI(
            model=request.model,
            base_url=request.api_base,
            api_key=request.api_key,
            temperature=request.temperature,
        )
    else:
        base_url = request.ollama_base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        return ChatOllama(
            model=request.model,
            base_url=base_url,
            temperature=request.temperature,
            reasoning=False,
        )

# ---------- API 端点 ----------
@app.on_event("startup")
async def startup():
    build_index()
    retriever = get_retriever(rebuild=True)
    logger.info("Cognitive Enhancer API started")

# ---------- HTTP 端点（对外 Agent 使用，纯 OpenAI 兼容）----------
@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    messages_json = format_messages_to_json(request.messages)
    tools_json = json.dumps(request.tools, ensure_ascii=False) if request.tools else ""
    llm = get_llm(request)

    # 调用增强层核心函数（同步，返回完整结果）
    result = run_self_reflection(
        input_text=messages_json,
        tools_text=tools_json,
        llm=llm
    )
    final_answer = result["final_answer"]   # 仅使用最终答案，思考过程不对外发送

    chunk_id = f"chatcmpl-{uuid.uuid4().hex}"
    created = int(time.time())

    # 使用三层防御解析最终答案
    parsed = parse_openai_response(final_answer, request.tools, llm=llm)
    tool_calls = parsed["tool_calls"]
    content = parsed["content"]

    if request.stream:
        # 流式响应：只发送最终答案的分块
        return StreamingResponse(
            generate_stream_response(content, tool_calls, request.model, chunk_id, created),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            }
        )
    else:
        message = {"role": "assistant", "content": content}
        if tool_calls:
            message["tool_calls"] = [
                {
                    "id": f"call_{uuid.uuid4().hex[:8]}",
                    "type": "function",
                    "function": {
                        "name": tc["name"],
                        "arguments": json.dumps(tc["arguments"])
                    }
                }
                for tc in tool_calls
            ]
        # 不添加任何非标准字段（移除 reasoning_content）
        return ChatCompletionResponse(
            id=chunk_id,
            created=created,
            model=request.model,
            choices=[{"index": 0, "message": message, "finish_reason": "stop"}],
            usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        )

# ---------- WebSocket 端点（客户端管理平台专用，实时推送思考过程）----------
@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    await websocket.accept()
    logger.info(f"WebSocket connected: {websocket.client}")
    try:
        while True:
            data = await websocket.receive_text()
            req = json.loads(data)
            messages = req.get("messages", [])
            model = req.get("model", "qwen2.5:7b")
            temperature = req.get("temperature", 0.7)
            tools = req.get("tools", [])
            api_base = req.get("api_base")
            api_key = req.get("api_key")
            ollama_base_url = req.get("ollama_base_url")

            # 构造临时请求对象用于 get_llm
            class DummyRequest:
                pass
            dummy_req = DummyRequest()
            dummy_req.model = model
            dummy_req.temperature = temperature
            dummy_req.api_base = api_base
            dummy_req.api_key = api_key
            dummy_req.ollama_base_url = ollama_base_url
            llm = get_llm(dummy_req)

            messages_json = json.dumps(messages, ensure_ascii=False)
            tools_json = json.dumps(tools, ensure_ascii=False) if tools else ""

            # 使用异步生成器逐阶段发送
            async for stage_name, content in run_self_reflection_stages(messages_json, tools_json, llm):
                logger.info(f"WebSocket sending stage: {stage_name}, content length: {len(content)}")
                await websocket.send_text(json.dumps({"type": stage_name, "content": content}))
                logger.info(f"WebSocket sent {stage_name}")
                if stage_name == "output":
                    # 解析最终输出，提取纯文本内容（可同时发送 tool_calls，但客户端通常只需要文本）
                    parsed = parse_openai_response(content, tools, llm=llm)
                    final_content = parsed.get("content", "")
                    await websocket.send_text(json.dumps({"type": "output", "content": final_content}))
                else:
                    await websocket.send_text(json.dumps({"type": stage_name, "content": content}))
            await websocket.send_text(json.dumps({"type": "done"}))
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {websocket.client}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.close(code=1011, reason=str(e))