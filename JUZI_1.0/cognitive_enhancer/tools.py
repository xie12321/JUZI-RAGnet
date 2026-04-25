import os
import requests
from langchain.tools import StructuredTool
from pydantic import BaseModel, Field
from typing import Optional
from wiki_reader import get_personal_info

# ---------- web_search ----------
class WebSearchInput(BaseModel):
    query: str = Field(description="搜索关键词")
    max_results: int = Field(default=5, description="返回结果数量")

def web_search_func(query: str, max_results: int = 5) -> str:
    """Tavily 搜索（需设置 TAVILY_API_KEY）"""
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        return "错误：未设置 TAVILY_API_KEY"
    url = "https://api.tavily.com/search"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {"query": query, "search_depth": "basic", "max_results": max_results, "include_answer": False}
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if not data.get("results"):
            return f"未找到关于“{query}”的信息。"
        output = f"## 🔍 搜索结果（{query}）\n\n"
        for i, r in enumerate(data["results"], 1):
            output += f"### {i}. {r.get('title','无标题')}\n{r.get('content','')}\n来源：{r.get('url','#')}\n\n"
        return output
    except Exception as e:
        return f"搜索失败：{str(e)}"

web_search_tool = StructuredTool.from_function(
    func=web_search_func,
    name="web_search",
    description="通过互联网搜索实时信息，返回摘要和来源。",
    args_schema=WebSearchInput,
)

# ---------- recall_long_term_memory ----------
class RecallMemoryInput(BaseModel):
    query: str = Field(description="需要回忆的内容")
    k: int = Field(default=2, description="返回记忆条数")

def recall_memory_func(query: str, k: int = 2) -> str:
    info = get_personal_info(query)
    if info:
        return f"根据长期记忆，相关信息如下：\n{info}"
    else:
        return "没有找到相关记忆。"

recall_memory_tool = StructuredTool.from_function(
    func=recall_memory_func,
    name="recall_long_term_memory",
    description="从长期记忆中检索与当前问题相关的过往对话，支持按类别过滤。",
    args_schema=RecallMemoryInput,
)

all_tools = [web_search_tool, recall_memory_tool]
tool_map = {t.name: t for t in all_tools}