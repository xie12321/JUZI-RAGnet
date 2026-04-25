# wiki_compiler.py
import json
import re
from pathlib import Path
from typing import Dict, List, Optional
from langchain_core.messages import HumanMessage
from model import llm as default_llm
from wiki_reader import retrieve, find_doc_by_title
from wiki_graph import find_path
from logger_config import logger
from wiki_retriever import get_retriever
import frontmatter



def extract_concepts(text: str) -> List[str]:
    """简单提取文本中的概念"""
    quoted = re.findall(r'["\u201c\u201d]([^"\u201c\u201d]+)["\u201c\u201d]|\u300a([^\u300b]+)\u300b|\u300c([^\u300d]+)\u300d', text)
    concepts = []
    for q in quoted:
        for group in q:
            if group:
                concepts.append(group.strip())
                break
    if concepts:
        return concepts[:2]
    chinese_words = re.findall(r'[\u4e00-\u9fa5]{2,6}', text)
    stopwords = {'什么', '怎么', '为什么', '哪里', '哪个', '如何', '可以', '需要', '应该', '可能', '就是', '不是', '这个', '那个'}
    concepts = [w for w in chinese_words if w not in stopwords]
    return concepts[:2]


def compile_knowledge(query: str, context: str = "", categories: Optional[List[str]] = None, llm=None) -> str:

    retriever = get_retriever()
    results = retriever.hybrid_search_with_graph(query, categories=categories, top_k=10, expand_neighbors=True)

    # 添加检索日志
    logger.info(f"Retrieved {len(results)} documents for query: {query[:50]}... categories: {categories}")
    for i, res in enumerate(results[:3]):  # 只打印前3个
        logger.debug(f"  Result {i + 1}: {res['metadata'].get('title', 'No title')} (score: {res['score']:.3f})")

    if llm is None:
        llm = default_llm

    if not results:
        return "无相关知识。"

    # 提取文档内容（优先使用全文，否则使用摘要）
    docs_text = []
    for res in results:
        title = res['metadata'].get('title', '无标题')
        content = res.get('content', '')
        if not content:
            src_path = res['metadata'].get('source')
            if src_path and Path(src_path).exists():
                try:

                    with open(src_path, 'r', encoding='utf-8') as f:
                        post = frontmatter.load(f)
                    content = post.content[:1000]
                except:
                    content = res['metadata'].get('summary', '')
        docs_text.append(f"### {title}\n{content}")

    raw_text = "\n\n".join(docs_text)

    # 路径发现（保留）
    path_text = ""
    concepts = extract_concepts(query)
    if len(concepts) >= 2:
        start_doc = find_doc_by_title(concepts[0])
        end_doc = find_doc_by_title(concepts[1])
        if start_doc and end_doc:
            path = find_path(start_doc, end_doc)
            if path:
                path_text = "\n\n概念关联路径：" + " → ".join([p.stem for p in path]) + "\n"

    prompt = f"""你是知识编译专家。请根据以下原始文档，为用户问题「{query}」提炼出相关的知识，用简洁的条目列出。

上下文（若有）：{context}

{raw_text}
{path_text}

输出格式（纯文本，不要JSON）：
- 知识点1
- 知识点2
...
"""
    response = llm.invoke([HumanMessage(content=prompt)])
    return response.content


def extract_knowledge_from_conversation(conversation_text: str, llm=None) -> dict:
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