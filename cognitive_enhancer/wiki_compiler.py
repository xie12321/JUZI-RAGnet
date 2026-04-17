# wiki_compiler.py
import json
import re
from typing import Dict
from langchain_core.messages import HumanMessage
from model import llm
from wiki_reader import retrieve
from logger_config import logger

def compile_knowledge(query: str, context: str = "") -> Dict[str, str]:
    """
    使用 LLM 对检索到的文档进行深度编译，返回三类结构化知识。
    """
    # 1. 从三个知识库检索原始文档
    reasoning_docs = retrieve(query, category="reasoning", top_k=3)
    experience_docs = retrieve(query, category="experience", top_k=5)
    memory_docs = retrieve(query, category="memory", top_k=3)

    # 2. 构建原始文档文本（包含标题和内容摘要）
    def format_docs(docs):
        return "\n\n".join([f"### {d['title']}\n{d['content'][:1000]}" for d in docs])

    reasoning_raw = format_docs(reasoning_docs) if reasoning_docs else "无"
    experience_raw = format_docs(experience_docs) if experience_docs else "无"
    memory_raw = format_docs(memory_docs) if memory_docs else "无"

    # 3. 使用 LLM 编译知识
    prompt = f"""你是知识编译专家。请根据以下原始文档，为用户问题「{query}」提炼三类知识，输出 JSON。

上下文（若有）：{context}

## 推理库（思维框架、逻辑推理方法）
{reasoning_raw}

## 经验库（具体案例、公式、规律、失败教训）
{experience_raw}

## 记忆库（用户画像、历史事实）
{memory_raw}

输出格式（严格遵守 JSON，不要有其他文字）：
{{
  "reasoning": "提炼后的思维框架和逻辑方法，用简洁的条目列出",
  "experience": "提炼后的具体案例、公式、教训，用简洁的条目列出",
  "memory": "提炼后的用户画像或历史事实，用简洁的条目列出"
}}

如果某类知识为空，输出空字符串。
"""
    response = llm.invoke([HumanMessage(content=prompt)])
    content = response.content
    # 提取 JSON
    try:
        data = json.loads(content)
    except:
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group(0))
        else:
            logger.warning("Failed to parse JSON from LLM response, using raw summaries")
            data = {
                "reasoning": "\n".join([f"- {d['summary']}" for d in reasoning_docs]),
                "experience": "\n".join([f"- {d['summary']}" for d in experience_docs]),
                "memory": "\n".join([f"- {d['summary']}" for d in memory_docs])
            }
    return {
        "reasoning": data.get("reasoning", ""),
        "experience": data.get("experience", ""),
        "memory": data.get("memory", "")
    }


def extract_knowledge_from_conversation(conversation_text: str) -> dict:
    """
    从对话历史中提取可沉淀的三类知识，用于写入 Wiki。
    """
    prompt = f"""请分析以下对话历史，提取可以沉淀到知识库的信息，输出 JSON。

对话历史：
{conversation_text}

输出格式：
{{
  "reasoning": "提炼出的思维框架、推理方法（若无，留空）",
  "experience": "提炼出的具体案例、公式、规律、教训（若无，留空）",
  "memory": "提炼出的用户画像、偏好、历史事实（若无，留空）"
}}
"""
    response = llm.invoke([HumanMessage(content=prompt)])
    content = response.content
    try:
        data = json.loads(content)
    except:
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        data = json.loads(json_match.group(0)) if json_match else {}
    return {
        "reasoning": data.get("reasoning", ""),
        "experience": data.get("experience", ""),
        "memory": data.get("memory", "")
    }