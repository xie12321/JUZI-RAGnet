import time
import json
from wiki_reader import build_index
from controller import run_self_reflection
from wiki_compiler import extract_knowledge_from_conversation
from wiki_retriever import get_retriever
from wiki_writer import write_to_wiki
from logger_config import logger


def main():
    build_index()
    # 初始化混合检索器
    retriever = get_retriever(rebuild=False)
    print("混合检索器已就绪")
    print("Cognitive Enhancer CLI. Type 'exit' to quit.")

    # 存储完整的对话历史（OpenAI 格式）
    messages = []  # [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]
    conversation_counter = 0
    conversation_text = ""  # 累积的对话文本，用于提取知识（仍保留）

    try:
        while True:
            user_input = input("\nYou: ")
            if user_input.lower() == "exit":
                break

            # 将用户消息加入历史
            messages.append({"role": "user", "content": user_input})

            # 自省循环：处理可能的多轮工具调用
            while True:
                # 构造当前 messages 的 JSON 字符串
                input_text = json.dumps(messages, ensure_ascii=False)
                result_str = run_self_reflection(input_text=input_text, tools_text="")

                # 解析返回的 JSON
                try:
                    result = json.loads(result_str)
                    content = result.get("content", "")
                    tool_calls = result.get("tool_calls", [])
                except json.JSONDecodeError:
                    content = result_str
                    tool_calls = []

                # 如果没有工具调用，结束循环
                if not tool_calls:
                    final_answer = content
                    break

                # 有工具调用：模拟外部工具执行
                print(f"🔧 需要调用工具: {tool_calls}")
                # 这里简单模拟：假设每个工具调用都返回固定结果，或让用户输入
                # 实际应该根据工具名调用对应的函数，这里为演示，让用户手动输入结果
                tool_results = []
                for tc in tool_calls:
                    tool_name = tc.get("name", "unknown")
                    args = tc.get("arguments", {})
                    print(f"   工具: {tool_name}, 参数: {args}")
                    # 模拟执行结果（实际可调用本地函数）
                    result_text = input(f"请输入工具 '{tool_name}' 的执行结果: ")
                    tool_results.append({
                        "tool_call_id": tc.get("id", "call_unknown"),
                        "role": "tool",
                        "content": result_text
                    })
                # 将工具结果追加到 messages
                for tr in tool_results:
                    messages.append(tr)
                # 继续循环，让增强层处理工具结果

            # 输出最终答案
            print(f"AI: {final_answer}")

            # 将助手回复加入历史
            messages.append({"role": "assistant", "content": final_answer})

            # 更新用于知识沉淀的文本（原有逻辑）
            conversation_text += f"用户: {user_input}\nAI: {final_answer}\n\n"
            conversation_counter += 1

            # 如果还需要模拟多轮（原代码中的“需要的信息：”检测已不需要，因为工具调用已处理）
            # 但为了兼容可能输出的“需要的信息：”字符串，仍保留一段检测（可选）
            if "需要的信息：" in final_answer and not tool_calls:
                info = input("External info (simulated): ")
                # 将外部信息作为工具结果加入 messages
                messages.append({"role": "tool", "content": info, "tool_call_id": "manual"})
                # 再次调用增强层处理外部信息
                input_text = json.dumps(messages, ensure_ascii=False)
                result2_str = run_self_reflection(input_text=input_text, tools_text="")
                try:
                    result2 = json.loads(result2_str)
                    final_answer2 = result2.get("content", result2_str)
                except:
                    final_answer2 = result2_str
                print(f"AI (after info): {final_answer2}")
                messages.append({"role": "assistant", "content": final_answer2})
                conversation_text += f"外部信息: {info}\nAI: {final_answer2}\n\n"
                conversation_counter += 1

            # 每10次对话，沉淀知识（原有逻辑）
            if conversation_counter >= 10:
                logger.info("Ten conversations reached, extracting knowledge...")
                knowledge = extract_knowledge_from_conversation(conversation_text)
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                if knowledge["reasoning"]:
                    write_to_wiki("reasoning", f"Session_{timestamp}_reasoning", knowledge["reasoning"])
                if knowledge["experience"]:
                    write_to_wiki("experience", f"Session_{timestamp}_experience", knowledge["experience"])
                if knowledge["memory"]:
                    write_to_wiki("memory", f"Session_{timestamp}_memory", knowledge["memory"])
                # 重置计数器和文本
                conversation_counter = 0
                conversation_text = ""

    except KeyboardInterrupt:
        print("\nExiting...")
    finally:
        # 退出时，如果还有未沉淀的对话，也进行一次知识提取
        if conversation_counter > 0:
            logger.info("Extracting remaining knowledge before exit...")
            knowledge = extract_knowledge_from_conversation(conversation_text)
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            if knowledge["reasoning"]:
                write_to_wiki("reasoning", f"Exit_{timestamp}_reasoning", knowledge["reasoning"])
            if knowledge["experience"]:
                write_to_wiki("experience", f"Exit_{timestamp}_experience", knowledge["experience"])
            if knowledge["memory"]:
                write_to_wiki("memory", f"Exit_{timestamp}_memory", knowledge["memory"])
        print("Goodbye!")


if __name__ == "__main__":
    main()