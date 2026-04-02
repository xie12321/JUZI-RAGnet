import json
import os
import time
from typing import List, Dict, Optional
from langchain.memory import ConversationBufferMemory
from langchain_core.messages import HumanMessage, AIMessage
from logger_config import logger

MID_TERM_FILE = "mid_term_memory.json"

class MidTermMemory:
    def __init__(self, max_messages: int = 30, importance_keywords: List[str] = None):
        self.max_messages = max_messages
        self.importance_keywords = importance_keywords or ["记住", "重要", "不要忘记", "我的名字", "我叫"]
        self.messages = []
        self.load()

    def load(self):
        if os.path.exists(MID_TERM_FILE):
            try:
                with open(MID_TERM_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.messages = data.get("messages", [])
                    print(f"📂 加载中期记忆：{len(self.messages)} 条消息")
            except Exception as e:
                print(f"加载中期记忆失败: {e}")
                self.messages = []

    def save(self):
        try:
            with open(MID_TERM_FILE, 'w', encoding='utf-8') as f:
                json.dump({"messages": self.messages}, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存中期记忆失败: {e}")

    def add_message(self, role: str, content: str):
        self.messages.append({"role": role, "content": content, "timestamp": time.time()})
        if len(self.messages) > self.max_messages:
            self._compress()

    def add_messages_batch(self, messages: List[Dict[str, str]]):
        for msg in messages:
            self.messages.append(msg)
        if len(self.messages) > self.max_messages:
            self._organize()

    def _compress(self):
        important_facts = []
        remaining_messages = []
        for msg in self.messages:
            if any(kw in msg["content"] for kw in self.importance_keywords):
                important_facts.append(msg["content"])
            else:
                remaining_messages.append(msg)

        if important_facts:
            try:
                from memory import memory_kb
                for fact in important_facts:
                    memory_kb.add_texts([fact], metadatas=[{"source": "mid_term_important"}])
                print(f"🧠 已将 {len(important_facts)} 条重要信息存入长期记忆")
            except Exception as e:
                print(f"存入长期记忆失败: {e}")

        self.messages = remaining_messages[-self.max_messages//2:]

    def _summarize_old_messages(self, keep_count: int = 5):
        if len(self.messages) <= keep_count:
            return
        old_messages = self.messages[:-keep_count]
        recent_messages = self.messages[-keep_count:]

        history_text = "\n".join([f"{m['role']}: {m['content']}" for m in old_messages])
        from model import llm
        from langchain_core.messages import HumanMessage
        prompt = f"""请将以下对话历史概括为一段简短的文字（不超过100字），保留关键信息：
{history_text}
"""
        try:
            response = llm.invoke([HumanMessage(content=prompt)])
            summary = response.content.strip()
            summary_msg = {"role": "summary", "content": f"（对话摘要）{summary}", "timestamp": time.time()}
            self.messages = [summary_msg] + recent_messages
            print(f"📝 已将 {len(old_messages)} 条消息概括为摘要")
        except Exception as e:
            print(f"概括失败: {e}")

    def organize(self, short_term_messages: List[Dict[str, str]]):
        self.add_messages_batch(short_term_messages)
        self.messages.sort(key=lambda x: x["timestamp"])
        if len(self.messages) > self.max_messages:
            self._compress()
            self._summarize_old_messages(keep_count=5)
        self.save()

    def llm_organize(self, short_term_messages: List[Dict[str, str]]):
        """使用 LLM 驱动的自省循环整理记忆"""
        from memory_organizer import build_memory_organizer
        from memory_organizer.state import MemoryState

        # 合并短期记忆到中期记忆
        self.messages.extend(short_term_messages)
        self.messages.sort(key=lambda x: x["timestamp"])

        # 调用整理图
        state = MemoryState(
            messages=self.messages,
            iteration=0,
            important=[],
            summary=None
        )
        app = build_memory_organizer()
        final_state = app.invoke(state)

        # 将重要信息存入长期记忆
        if final_state["important"]:
            from memory import memory_kb
            for fact in final_state["important"]:
                memory_kb.add_texts([fact], metadatas=[{"source": "llm_organizer"}])
            print(f"🧠 已将 {len(final_state['important'])} 条重要信息存入长期记忆")

        # 更新中期记忆
        if final_state["summary"]:
            self.messages = [{
                "role": "summary",
                "content": final_state["summary"],
                "timestamp": time.time()
            }]
        else:
            self.messages = []

        self.save()

    def restore_to_buffer_memory(self, buffer_memory: ConversationBufferMemory):
        for msg in self.messages:
            if msg["role"] == "user":
                buffer_memory.chat_memory.add_user_message(msg["content"])
            elif msg["role"] == "assistant":
                buffer_memory.chat_memory.add_ai_message(msg["content"])
            elif msg["role"] == "summary":
                buffer_memory.chat_memory.add_ai_message(msg["content"])
        print(f"🔄 已将 {len(self.messages)} 条中期记忆恢复到短期记忆")