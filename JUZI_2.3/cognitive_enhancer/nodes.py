# nodes.py
import json
import re

from langchain_core.messages import HumanMessage
from model import llm, OpenAIResponse
from logger_config import logger
from model import structured_output_llm
from model import llm as default_llm


def think_node(state_json: dict) -> str:
    context = state_json["peripheral"]["input"]
    tools_def = state_json["peripheral"].get("tools", "")
    knowledge = state_json["internal"]["think_knowledge"]   # 思考池上下文
    llm = state_json["peripheral"].get("llm", default_llm)
    previous_reflection = state_json["internal"].get("previous_reflection", "")

    prompt = f"""你现在处于【觉察与拆解】阶段。

    请仔细阅读对话历史、可用工具以及思考池中的内容，然后对用户问题进行深入拆解。

在思考中，当你发现自己对某个概念不确定、或需要更多信息来支撑判断时，直接在文中自然地说出你的检索需求。例如：
- “……这里我需要查一下[关键词]，才能确定……”
- “……关于[某个假设]，我应该加载[文档名]来核实……”

    【外部输入】（包含完整的对话历史，JSON格式，包含user/assistant/system/tool等消息）：{context}
    【可用工具】：{tools_def if tools_def else "无"}
    【当前思考池内容】：
    {knowledge}"""

    if previous_reflection:
        prompt += f"""

    在上一次反思中，发现了以下需要修正的问题。请务必在本次检索指导中重点考虑这些问题：
    【上一轮反思指出的问题】：
    {previous_reflection}"""

    prompt += """

    请以第一人称“我”自然地写下你的初步思考。用连贯的段落表达你的推理过程，检索需求直接融入在推理中，不需要单独列出。"""

    response = llm.invoke([HumanMessage(content=prompt)])
    return response.content


def connect_node(state_json: dict) -> str:
    context = state_json["peripheral"]["input"]
    tools_def = state_json["peripheral"].get("tools", "")
    # ⭐ 改用思考池融合后的最新上下文，而非旧的 think_out
    knowledge = state_json["internal"]["connect_knowledge"]
    think_out = state_json["internal"]["think_output"]
    llm = state_json["peripheral"].get("llm", default_llm)

    prompt = f"""你现在处于【关联与构建】阶段。

    请仔细阅读思考池中的全部内容，然后将分析转化为一个实际可行的方案。

在构建方案时，如果发现缺少某些案例、数据、或具体的操作细节，直接在文中自然地说出你需要的补充信息。例如：
- “……我需要一个关于[具体场景]的案例来支撑这一步……”
- “……这一步的可行性取决于[某个数据]，我需要检索……”

    【外部输入】（包含完整的对话历史，JSON格式，包含user/assistant/system/tool等消息）：{context}
    【可用工具】：{tools_def if tools_def else "无"}
    【初步检索指导】：
    {think_out}
    【当前思考池内容】：
    {knowledge}

    请以第一人称“我”自然地写下你的深化方案。推理和检索需求自然融合，用连贯的段落表达。"""

    response = llm.invoke([HumanMessage(content=prompt)])
    return response.content


def reflect_node(state_json: dict) -> str:
    context = state_json["peripheral"]["input"]
    tools_def = state_json["peripheral"].get("tools", "")
    # ⭐ 改用思考池融合后的最新上下文，而非旧的 think_out 和 connect_out
    knowledge = state_json["internal"]["reflect_knowledge"]
    llm = state_json["peripheral"].get("llm", default_llm)

    prompt = f"""接下来是【自我审视与检验】阶段。

    现在你需要停下来，审视一下你之前的整个思考过程。

请真诚地问自己：
- 我的方案有没有逻辑跳跃或矛盾的地方？
- 有没有什么重要的前置条件、隐含假设被我想当然地接受了？
- 有没有边界情况或反例被忽略了？
- 如果发现了漏洞，我该怎么修正？如果思考已经足够周全，也请说明理由。

【外部输入】（包含完整的对话历史，JSON格式，包含user/assistant/system/tool等消息）：{context}
【可用工具】：{tools_def if tools_def else "无"}
【思考池当前内容】：
{knowledge}

请以第一人称"我"自然地写下你的自我审视。不要用检查清单格式，就像在心里对自己说话一样。

记住：要诚实地评估，不编造问题，也不掩盖缺陷，不要没有漏洞硬挑刺。"""

    response = llm.invoke([HumanMessage(content=prompt)])
    return response.content


def output_node(state_json: dict) -> str:
    context = state_json["peripheral"]["input"]
    tools_def = state_json["peripheral"].get("tools", "")
    llm = state_json["peripheral"].get("llm", default_llm)

    # 优先使用思考池融合后的完整上下文
    pool_context = state_json["internal"].get("final_context", "")
    if pool_context:
        prompt = f"""你已经完成了对问题的深度思考，思考池已演化出以下内容。请基于这些内容生成最终回答。

【思考池内容】：
{pool_context}

【外部输入】（包含完整的对话历史，JSON格式，包含user/assistant/system/tool等消息）：{context}
【可用工具】：{tools_def if tools_def else "无"}
现在，请根据以上所有的思考，生成一个最终的回答。直接输出纯文本答案，不要JSON。"""
    else:
        think_out = state_json["internal"]["think_output"]
        connect_out = state_json["internal"]["connect_output"]
        reflect_out = state_json["internal"]["reflect_output"]
        prompt = f"""你已经完成了从初步思考、方案构建到自我反思的完整过程。

现在，请根据以上所有的思考，生成一个最终的回答。直接输出纯文本答案，不要JSON。

【外部输入】（包含完整的对话历史，JSON格式，包含user/assistant/system/tool等消息）：{context}
【可用工具】：{tools_def if tools_def else "无"}
【初步思考】：
{think_out}
【具体方案】：
{connect_out}
【自我反思】：
{reflect_out}

请输出最终回答："""

    # 纯文本输出
    try:
        raw = llm.invoke([HumanMessage(content=prompt)]).content
        safe = OpenAIResponse(tool_calls=[], content=raw)
        return safe.model_dump_json()
    except Exception as e2:
        logger.error(f"Failed to parse output: {e2}")
        safe = OpenAIResponse(
            tool_calls=[],
            content="抱歉，我暂时无法生成有效回答，请稍后重试。"
        )
        return safe.model_dump_json()


def output_node_plain(state_json: dict) -> str:
    context = state_json["peripheral"]["input"]
    llm = state_json["peripheral"].get("llm")

    pool_context = state_json["internal"].get("final_context", "")
    if pool_context:
        prompt = f"""你已经完成了对问题的深度思考，思考池已演化出以下内容。请基于这些内容生成最终回答。

【思考池内容】：
{pool_context}

【外部输入】（包含完整的对话历史，JSON格式，包含user/assistant/system/tool等消息）：{context}
现在，请根据以上所有的思考，生成一个最终的回答。回答应该清晰、正式、可以直接呈现给用户。如果需要引用知识，请自然地融入回答中。

请输出最终回答："""
    else:
        think_out = state_json["internal"]["think_output"]
        connect_out = state_json["internal"]["connect_output"]
        reflect_out = state_json["internal"]["reflect_output"]
        prompt = f"""你已经完成了从初步思考、方案构建到自我反思的完整过程。

现在，请根据以上所有的思考，生成一个最终的回答。回答应该清晰、正式和亲切友善，可以直接呈现给用户。如果需要引用知识，请自然地融入回答中。

【外部输入】（包含完整的对话历史，JSON格式，包含user/assistant/system/tool等消息）：{context}
【初步思考】：
{think_out}
【具体方案】：
{connect_out}
【自我反思】：
{reflect_out}

请输出最终回答："""
    response = llm.invoke([HumanMessage(content=prompt)])
    return response.content