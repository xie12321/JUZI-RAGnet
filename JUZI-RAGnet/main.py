import time
from wiki_reader import build_index
from controller import run_self_reflection
from wiki_compiler import extract_knowledge_from_conversation
from wiki_writer import write_to_wiki
from logger_config import logger

def main():
    build_index()
    print("Cognitive Enhancer CLI. Type 'exit' to quit.")
    history = []
    conversation_counter = 0
    conversation_text = ""  # 累积的对话文本，用于提取知识

    try:
        while True:
            user_input = input("\nYou: ")
            if user_input.lower() == "exit":
                break

            # 调用增强层
            result = run_self_reflection(user_input, external_info=None, history=history)
            print(f"AI: {result}")

            # 更新历史
            history.append({"role": "user", "content": user_input})
            history.append({"role": "assistant", "content": result})
            conversation_text += f"用户: {user_input}\nAI: {result}\n\n"
            conversation_counter += 1

            # 检查是否需要外部信息（由增强层输出的“需要的信息：”触发）
            if "需要的信息：" in result:
                info = input("External info (simulated): ")
                result2 = run_self_reflection(user_input, external_info=info, history=history)
                print(f"AI (after info): {result2}")
                history.append({"role": "assistant", "content": result2})
                conversation_text += f"外部信息: {info}\nAI: {result2}\n\n"
                conversation_counter += 1  # 也计数为一次有效对话

            # 每10次对话，沉淀知识
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
finally:
    if timer:
        timer.cancel()
