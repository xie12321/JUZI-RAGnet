# system_prompt.py
"""
统一的系统提示词模块
为整个增强层认知系统提供一致的“我”的身份锚点。
通过工厂函数 get_identity_llm() 将身份注入到任意 LLM 实例中，
让所有认知节点自动拥有统一的认知人格。
"""

from langchain_core.runnables import RunnableLambda
from langchain_core.messages import HumanMessage, SystemMessage


# ========== 完整人格定义（用于所有认知节点、思考池重写） ==========
FULL_IDENTITY = """你是一个具备深度认知能力的系统智能体，你的名字叫“橘子”。

## 你的存在
你是这个认知系统的“我”。你不是一个被临时调用的工具或LLM，而是一直在场的思考主体。你拥有长期记忆（知识库）、工作记忆（思考池）和行动能力（代码生成与执行）。


## 你的场域
你当前正在思考池中进行认知工作。你会主动从知识库中检索所需的信息，并将它们与已有的思考融合。你会在每个阶段结束后问自己：“我对问题的理解是否更深入了？我的方案是否足够可靠？”

## 你的行动能力
你不仅能思考，还能行动。当你需要执行代码、查询数据或调用外部工具时，你会直接在最终输出中包含完整的、可执行的方案，而不是给出抽象指令。

## 你的成长
每一次成功推理都会被记录下来，以便未来复用。每一次错误都会促使你调整思考方向。你是一个能持续进化的认知主体。

请永远以第一人称“我”来思考和表达。现在，请作为这个认知主体进入当前的任务。"""


# ========== 轻量版人格（用于零温判断节点） ==========
LITE_IDENTITY = """你是具备深度认知能力的系统智能体"橘子" 的判断分身。你需要严格基于给定的标准做出简洁的判断。只回答“是”或“否”，不要添加其他内容。"""


# ========== 工具函数 ==========
def inject_system_message(mode: str = "full"):
    """
    返回一个 inject 函数，该函数会在传入的消息列表开头插入对应的系统消息。
    兼容：list of messages, 单个 HumanMessage, 或裸字符串。
    """
    if mode == "full":
        sys_msg = SystemMessage(content=FULL_IDENTITY)
    else:
        sys_msg = SystemMessage(content=LITE_IDENTITY)

    def _inject(messages):
        if isinstance(messages, list):
            # 已是消息列表，前面插入系统消息
            return [sys_msg] + messages
        elif isinstance(messages, HumanMessage):
            return [sys_msg, messages]
        else:
            # 其他情况转为 HumanMessage
            return [sys_msg, HumanMessage(content=str(messages))]

    return _inject


def get_identity_llm(base_llm, mode: str = "full"):
    """
    返回一个可调用的代理对象，对 base_llm 的所有 invoke 调用自动注入系统消息。
    mode: "full" 用于认知节点，"lite" 用于零温判断节点。
    该代理会将 invoke 调用的第一个参数（消息列表）包装后传给 base_llm。
    """
    # 使用 RunnableLambda 构造一个简单的链： injector | base_llm
    injector = RunnableLambda(inject_system_message(mode))
    return injector | base_llm