# tools/recall_memory.py
from memory import memory_kb
from utils import guess_categories

def recall_memory_func(query: str, k: int = 2) -> str:
    """从长期记忆库检索过往对话（按类别过滤）"""
    if memory_kb is None:
        return "错误：长期记忆库未初始化"
    target_cats = guess_categories(query)
    docs = memory_kb.similarity_search(query, k=k*3)
    filtered = [doc for doc in docs if doc.metadata.get("category") in target_cats][:k]
    if not filtered:
        return "没有找到相关记忆。"
    output = "根据长期记忆，以下是相关的过去对话：\n"
    for i, doc in enumerate(filtered, 1):
        output += f"{i}. {doc.page_content}\n"
    return output