# utils.py
from typing import List

def guess_categories(query: str) -> List[str]:
    """简单类别猜测，用于长期记忆检索（可扩展）"""
    return ["闲聊"]

def classify_dialogue(user_msg: str, ai_msg: str) -> str:
    """简单对话分类，用于长期记忆存储（可扩展）"""
    return "闲聊"