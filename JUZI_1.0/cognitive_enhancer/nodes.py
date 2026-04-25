# nodes.py
from langchain_core.messages import HumanMessage
from model import llm, OpenAIResponse
from logger_config import logger
from model import structured_output_llm
from model import llm as default_llm

def think_node(state_json: dict) -> str:
    context = state_json["peripheral"]["input"]
    tools_def = state_json["peripheral"].get("tools", "")
    knowledge = state_json["internal"]["think_knowledge"]   # 字符串
    llm = state_json["peripheral"].get("llm", default_llm)  # 获取 llm
    prompt = f"""外部输入（包含完整的对话历史，JSON 格式，包含 user/assistant/system/tool 等消息）：{context}
    可用工具定义（JSON）：
{tools_def if tools_def else "无"}
【知识】：{knowledge}
结合用户的提问，上下文，还有知识。请进行初步思考，列出关键问题、分析角度。输出格式：
思考：..."""
    response = llm.invoke([HumanMessage(content=prompt)])
    return response.content

def connect_node(state_json: dict) -> str:
    context = state_json["peripheral"]["input"]
    tools_def = state_json["peripheral"].get("tools", "")
    think_out = state_json["internal"]["think_output"]
    knowledge = state_json["internal"]["connect_knowledge"]   # 字符串
    llm = state_json["peripheral"].get("llm", default_llm)
    prompt = f"""外部输入（包含完整的对话历史，JSON 格式，包含 user/assistant/system/tool 等消息）：{context}
    可用工具定义（JSON）：
{tools_def if tools_def else "无"}
初步思考：{think_out}
【知识】：{knowledge}
根据初步思考，结合可用工具定义和知识，请深化思考，提出具体方案。如需调用外部工具，请提示出指定格式（如openai的工具调用输出格式规范）。
输出格式：
连接思考：...
具体方案：..."""
    response = llm.invoke([HumanMessage(content=prompt)])
    return response.content

def reflect_node(state_json: dict) -> str:
    context = state_json["peripheral"]["input"]
    tools_def = state_json["peripheral"].get("tools", "")
    think_out = state_json["internal"]["think_output"]
    connect_out = state_json["internal"]["connect_output"]
    knowledge = state_json["internal"]["reflect_knowledge"]   # 字符串
    llm = state_json["peripheral"].get("llm", default_llm)
    prompt = f"""外部输入（包含完整的对话历史，JSON 格式，包含 user/assistant/system/tool 等消息）：{context}
    可用工具定义（JSON）：
{tools_def if tools_def else "无"}
初步思考：{think_out}
连接思考：{connect_out}
【知识】：{knowledge}
根据上述思考过程和知识并结合用户的提问和上下文，请反思合理性、找出漏洞。输出格式：
反思：...
改进建议：..."""
    response = llm.invoke([HumanMessage(content=prompt)])
    return response.content


def output_node(state_json: dict) -> str:
    context = state_json["peripheral"]["input"]
    tools_def = state_json["peripheral"].get("tools", "")
    think_out = state_json["internal"]["think_output"]
    connect_out = state_json["internal"]["connect_output"]
    reflect_out = state_json["internal"]["reflect_output"]
    llm = state_json["peripheral"].get("llm", default_llm)
    structured_output_llm = llm.with_structured_output(OpenAIResponse)
    prompt = f"""外部输入（包含完整的对话历史，JSON 格式，包含 user/assistant/system/tool 等消息）：{context}
    可用工具定义（JSON）：
{tools_def if tools_def else "无"}
初步思考：{think_out}
连接思考：{connect_out}
最终思考：{reflect_out}
【重要】请根据以上思考过程，生成最终回答。如果需要调用工具，必须严格按照以下 JSON 格式输出：
{{"tool_calls": [{{"name": "工具名", "arguments": {{"参数名": "参数值"}}}}], "content": ""}}
如果不需要调用工具，输出：
{{"tool_calls": [], "content": "你的回答"}}
只输出 JSON，不要输出任何其他格式的文本。"""
    try:
        response = structured_output_llm.invoke([HumanMessage(content=prompt)])
        # 如果 response 为 None，抛出异常
        if response is None:
            raise ValueError("structured output returned None")
        return response.model_dump_json()
    except Exception as e:
        logger.error(f"Structured output failed: {e}, falling back to safe JSON")
        # 降级：返回安全的默认 JSON
        safe_response = OpenAIResponse(
            tool_calls=[],
            content="抱歉，我暂时无法生成有效回答，请稍后重试。"
        )
        return safe_response.model_dump_json()