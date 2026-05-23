import json
import re
from typing import List, Dict

from model import OpenAIResponse, llm as default_llm, fix_llm as global_fix_llm
from langchain_core.messages import HumanMessage



def parse_openai_response(result_text: str, tools: List[Dict] = None, llm=None) -> Dict:
    """
    三层防御：
    1. 直接解析 JSON（结构化输出结果）
    2. 如果失败，用结构化输出 LLM 修复
    3. 如果仍失败，用正则兜底提取工具调用
    """
    # ---------- L1: 直接解析 ----------
    try:
        data = json.loads(result_text)
        if "tool_calls" in data and "content" in data:
            return data
        else:
            # 纯文本包装
            return {"tool_calls": [], "content": result_text}
    except:
        pass

    # ---------- L2: 结构化输出 LLM 修复 ----------
    fixed = _fix_with_structured_llm(result_text, tools, llm=llm)
    if fixed:
        return fixed

    # ---------- L3: 正则兜底 ----------
    return _regex_extract_tool_calls(result_text, tools)


def _fix_with_structured_llm(broken_text: str, tools: List[Dict] = None, llm=None) -> Dict | None:
    """调用结构化输出 LLM 修复格式，返回字典或 None"""
    # 如果没有传入 llm，则使用全局 fix_llm（或 default_llm）
    if llm is None:
        llm = global_fix_llm if global_fix_llm is not None else default_llm
    # 动态创建结构化输出 LLM
    try:
        structured_llm = llm.with_structured_output(OpenAIResponse)
    except Exception as e:
        # 如果模型不支持结构化输出，回退
        return None

    tool_hint = ""
    if tools:
        tool_names = [t['function']['name'] for t in tools]
        tool_hint = f"可用工具：{', '.join(tool_names)}。"

    fix_prompt = f"""你的任务是将以下文本中的工具调用转换为标准格式。
{tool_hint}
输出格式：{{"tool_calls": [{{"name": "工具名", "arguments": {{...}}}}], "content": "..."}}
如果文本中没有工具调用，tool_calls 为空数组，content 填入原文。

文本：
{broken_text}

只输出 JSON，不要输出其他文字。"""

    try:
        response = structured_llm.invoke([HumanMessage(content=fix_prompt)])
        # response 是 OpenAIResponse 对象
        return response.model_dump()
    except Exception:
        return None


def _regex_extract_tool_calls(text: str, tools: List[Dict] = None) -> Dict:
    """正则兜底，提取简单的工具调用模式"""
    tool_calls = []
    remaining = text
    tool_names = [t['function']['name'] for t in tools] if tools else []

    for tool_name in tool_names:
        # 匹配模式: 工具名(参数) 或 工具名: 参数 或 工具名 参数
        patterns = [
            rf'{re.escape(tool_name)}\s*\(\s*(\{{.*?\}}|\"[^\"]+\"|[^)]+)\s*\)',
            rf'{re.escape(tool_name)}\s*:\s*(\{{.*?\}}|\"[^\"]+\")',
            rf'{re.escape(tool_name)}\s+([^,\n]+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, remaining, re.IGNORECASE | re.DOTALL)
            if match:
                param_str = match.group(1).strip()
                try:
                    if param_str.startswith('{'):
                        args = json.loads(param_str)
                    elif param_str.startswith('"'):
                        args = {"query": param_str.strip('"')}
                    else:
                        # 简单 key=value 形式
                        args = dict(re.findall(r'(\w+)=([^,\s]+)', param_str))
                except:
                    args = {"query": param_str}
                tool_calls.append({"name": tool_name, "arguments": args})
                remaining = remaining.replace(match.group(0), '', 1).strip()
                break

    return {"tool_calls": tool_calls, "content": remaining}