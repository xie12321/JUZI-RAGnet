from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from config import LLM_MODEL, LLM_BASE_URL, LLM_API_KEY
from pydantic import BaseModel
from typing import List, Dict, Any

if "ollama" in LLM_BASE_URL or "localhost" in LLM_BASE_URL:
    llm = ChatOllama(model=LLM_MODEL, base_url=LLM_BASE_URL, temperature=0.7, reasoning=False)
else:
    llm = ChatOpenAI(model=LLM_MODEL, base_url=LLM_BASE_URL, api_key=LLM_API_KEY, temperature=0.7)

# 修复节点：低温度，确保格式正确
fix_llm = ChatOllama(model=LLM_MODEL, temperature=0.2)

class ToolCall(BaseModel):
    name: str
    arguments: Dict[str, Any]

class OpenAIResponse(BaseModel):
    tool_calls: List[ToolCall] = []
    content: str = ""

# 主结构化输出 LLM（用于 output_node）
structured_output_llm = llm.with_structured_output(OpenAIResponse)

# 修复专用结构化 LLM（可使用相同实例，也可单独创建）
fix_structured_llm = fix_llm.with_structured_output(OpenAIResponse)