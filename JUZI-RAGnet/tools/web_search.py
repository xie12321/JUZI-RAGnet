# tools/web_search.py
import os
import requests
from dotenv import load_dotenv

load_dotenv()

def web_search_func(query: str, max_results: int = 5) -> str:
    """执行联网搜索，返回格式化结果"""
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        return "错误：未设置 TAVILY_API_KEY 环境变量"

    url = "https://api.tavily.com/search"
    payload = {
        "api_key": api_key,
        "query": query,
        "search_depth": "basic",
        "max_results": max_results,
        "include_answer": False,
        "include_raw_content": False
    }
    try:
        resp = requests.post(url, json=payload, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if not data.get("results"):
            return f"未找到关于“{query}”的信息。"

        results = data["results"]
        output = f"## 🔍 搜索结果（{query}）\n\n"
        for i, r in enumerate(results, 1):
            output += f"### {i}. {r.get('title','无标题')}\n"
            output += f"{r.get('content','')}\n"
            output += f"来源：{r.get('url','#')}\n\n"
        return output
    except Exception as e:
        return f"搜索失败：{str(e)}"