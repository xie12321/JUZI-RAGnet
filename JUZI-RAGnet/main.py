import time
import threading
import sys
import torch
from dotenv import load_dotenv
from langchain.memory import ConversationBufferMemory
from langchain_core.messages import HumanMessage, AIMessage

from model import llm, Plan
from memory import memory_kb, experience_kb, reasoning_kb
from graph.builder import build_graph
from mid_term_memory import MidTermMemory
from logger_config import logger

load_dotenv()

# 短期记忆
memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)

# 中期记忆
mid_mem = MidTermMemory(max_messages=30)
mid_mem.restore_to_buffer_memory(memory)

# 构建 LangGraph 智能体
app = build_graph()

# ---------- 超时处理 ----------
IDLE_TIMEOUT = 600  # 10分钟
timer = None

def memory_organize(is_timeout=False):
    if is_timeout:
        print("\n⏰ 长时间未操作，开始记忆整理...")
    else:
        print("\n🧹 开始记忆整理...")
    # 收集短期记忆中的所有消息
    short_term = []
    for msg in memory.chat_memory.messages:
        if isinstance(msg, HumanMessage):
            short_term.append({
                "role": "user",
                "content": msg.content,
                "timestamp": time.time()
            })
        elif isinstance(msg, AIMessage):
            short_term.append({
                "role": "assistant",
                "content": msg.content,
                "timestamp": time.time()
            })
    # 调用中期记忆的 LLM 整理方法
    mid_mem.llm_organize(short_term)
    print("✅ 记忆整理完成，程序退出。")
    sys.exit(0)

def reset_timer():
    global timer
    if timer:
        timer.cancel()
    timer = threading.Timer(IDLE_TIMEOUT, lambda: memory_organize(is_timeout=True))
    timer.start()

# ---------- 主循环 ----------
print("🎤 数字人已启动，输入 'exit' 退出")

try:
    while True:
        reset_timer()
        user_input = input("\n请输入内容：")
        if user_input.lower() in ["exit", "quit"]:
            memory_organize(is_timeout=False)
            break

        memory.chat_memory.add_user_message(user_input)
        mid_mem.add_message("user", user_input)

        initial_state = {
            "user_input": user_input,
            "messages": memory.chat_memory.messages.copy(),
            "iteration": 0,
            "plan": None,
            "experiences": None,
            "tool_results": None,
            "tool_results_dict": None,
            "verification_passed": None,
            "verification_feedback": None,
            "error_found": None,
            "final_answer": None,
        }

        final_plan = None
        final_verification_passed = None
        final_answer = None

        for step in app.stream(initial_state):
            for node_name, node_output in step.items():
                print(f"\n--- 节点：{node_name} ---")
                if node_name == "planning":
                    final_plan = node_output.get("plan")
                    if final_plan:
                        print(f"📋 规划：{final_plan[:200]}...")
                elif node_name == "experience":
                    experiences = node_output.get("experiences")
                    if experiences:
                        print(f"📚 经验：{experiences}")
                elif node_name == "execute_tools":
                    tool_results = node_output.get("tool_results")
                    if tool_results:
                        print(f"🔧 工具执行结果：{tool_results[:300]}...")
                elif node_name == "verify":
                    final_verification_passed = node_output.get("verification_passed")
                    feedback = node_output.get("verification_feedback")
                    print(f"✅ 验证通过：{final_verification_passed}")
                    if feedback:
                        print(f"💬 验证反馈：{feedback}")
                elif node_name == "error_check":
                    error_found = node_output.get("error_found")
                    if error_found:
                        print(f"⚠️ 发现错误：{node_output.get('error_info', '')}")
                elif node_name == "output":
                    final_answer = node_output.get("final_answer")
                    print(f"🎤 最终回答：{final_answer}")

        memory.chat_memory.add_ai_message(final_answer)
        mid_mem.add_message("assistant", final_answer)
        print(f"橘子🍊: {final_answer}")

        # 存储成功经验
        if final_plan and final_verification_passed:
            try:
                plan_obj = Plan.model_validate_json(final_plan)
                if len(plan_obj.steps) > 0:
                    experience_text = f"## 任务：{user_input}\n### 执行计划：\n{plan_obj.model_dump_json(indent=2)}\n### 结果：\n{final_answer}"
                    experience_kb.add_texts(
                        [experience_text],
                        metadatas=[{"type": "success", "timestamp": time.time()}]
                    )
                    print("✅ 已将本次任务存入经验库")
            except Exception as e:
                print(f"存储经验失败: {e}")

        if torch.cuda.is_available():
            torch.cuda.empty_cache()

except KeyboardInterrupt:
    print("\n程序被用户中断")
    memory_organize(is_timeout=False)

finally:
    if timer:
        timer.cancel()