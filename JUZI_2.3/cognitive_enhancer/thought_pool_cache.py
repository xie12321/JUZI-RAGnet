# thought_pool_cache.py
import json
import time
from pathlib import Path
from typing import Dict, Optional
from langchain_core.messages import HumanMessage


class ThoughtPoolCache:
    """思考池暂存区：存储历史思考池，支持LLM相似性检索与命中统计"""

    def __init__(self, judge_llm, cache_dir: str = "./thought_pool_drafts"):
        self.judge_llm = judge_llm
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def save(self, pool_content: str, user_query: str, query_summary: str = ""):
        """保存思考池到暂存区。query_summary 可选，仅作为辅助标签，匹配时不依赖。"""
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        entry = {
            "user_query": user_query,
            "query_summary": query_summary,
            "pool_content": pool_content,
            "hit_count": 0,
            "created_at": timestamp,
            "last_hit_at": timestamp
        }
        filepath = self.cache_dir / f"{timestamp}.json"
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(entry, f, ensure_ascii=False)

    def find_best_match(self, current_query: str) -> Optional[Dict]:
        """使用预置的零温LLM判断当前问题是否与某个历史问题本质相同，若命中则返回该缓存条目。"""
        for cache_file in sorted(self.cache_dir.glob("*.json"), reverse=True):
            with open(cache_file, "r", encoding="utf-8") as f:
                entry = json.load(f)
            if self._is_similar(current_query, entry["user_query"]):
                entry["hit_count"] += 1
                entry["last_hit_at"] = time.strftime("%Y%m%d_%H%M%S")
                with open(cache_file, "w", encoding="utf-8") as f:
                    json.dump(entry, f, ensure_ascii=False)
                return entry
        return None

    def _is_similar(self, current_query: str, cached_query: str) -> bool:
        prompt = f"""判断以下两个问题是否本质属于同一类型，可以用相同的方法或思路解决。
当前问题：{current_query}
历史问题：{cached_query}
只回答“是”或“否”："""
        response = self.judge_llm.invoke([HumanMessage(content=prompt)])
        return response.content.strip() == "是"

    def get_all_entries(self) -> list:
        entries = []
        for f in self.cache_dir.glob("*.json"):
            with open(f, "r", encoding="utf-8") as fp:
                entries.append(json.load(fp))
        return entries

    def remove(self, timestamp: str):
        filepath = self.cache_dir / f"{timestamp}.json"
        if filepath.exists():
            filepath.unlink()