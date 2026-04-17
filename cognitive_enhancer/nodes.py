# nodes.py
from langchain_core.messages import HumanMessage
from model import llm
from logger_config import logger

def think_node(state_json: dict) -> str:
    user_input = state_json["peripheral"]["user_input"]
    reasoning = state_json["internal"]["compiled_knowledge"]["reasoning"]
    prompt = f"""用户问题：{user_input}
【推理库知识】：{reasoning}
请进行初步思考，列出关键问题、分析角度。输出格式：
思考：..."""
    response = llm.invoke([HumanMessage(content=prompt)])
    return response.content

def connect_node(state_json: dict) -> str:
    user_input = state_json["peripheral"]["user_input"]
    think_out = state_json["internal"]["think_output"]
    experience = state_json["internal"]["compiled_knowledge"]["experience"]
    memory = state_json["internal"]["compiled_knowledge"]["memory"]
    prompt = f"""用户问题：{user_input}
初步思考：{think_out}
【经验库知识】：{experience}
【记忆库知识】：{memory}
请深化思考，提出具体方案。输出格式：
连接思考：...
具体方案：..."""
    response = llm.invoke([HumanMessage(content=prompt)])
    return response.content

def reflect_node(state_json: dict) -> str:
    user_input = state_json["peripheral"]["user_input"]
    think_out = state_json["internal"]["think_output"]
    connect_out = state_json["internal"]["connect_output"]
    reasoning = state_json["internal"]["compiled_knowledge"]["reasoning"]
    experience = state_json["internal"]["compiled_knowledge"]["experience"]
    prompt = f"""用户问题：{user_input}
初步思考：{think_out}
连接思考：{connect_out}
【验证规则、逻辑方法】：{reasoning}
【失败案例、教训】：{experience}
请反思合理性、漏洞。输出格式：
反思：...
改进建议：..."""
    response = llm.invoke([HumanMessage(content=prompt)])
    return response.content

def output_node(state_json: dict) -> str:
    user_input = state_json["peripheral"]["user_input"]
    think_out = state_json["internal"]["think_output"]
    connect_out = state_json["internal"]["connect_output"]
    reflect_out = state_json["internal"]["reflect_output"]
    prompt = f"""用户问题：{user_input}
初步思考：{think_out}
连接思考：{connect_out}
最终思考：{reflect_out}
请根据以上的完整思考过程，生成最终回答。如需外部信息，请明确说明“需要的信息：...”。"""
    response = llm.invoke([HumanMessage(content=prompt)])
    return response.content