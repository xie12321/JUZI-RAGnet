# memory_organizer/state.py
from typing import List, Dict, Optional, TypedDict

class MemoryState(TypedDict):
    """记忆整理状态"""
    messages: List[Dict[str, any]]          # 待整理的消息列表，每条含 role, content, timestamp
    iteration: int                          # 当前迭代次数
    important: List[str]                    # 已提取的重要信息列表
    summary: Optional[str]                  # 最终生成的摘要