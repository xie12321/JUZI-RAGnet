import json
# controller.py
import json
from typing import Dict, Any, Optional
from copy import deepcopy
from nodes import think_node, connect_node, reflect_node, output_node
from wiki_compiler import compile_knowledge
from config import MAX_ITERATIONS
from logger_config import logger

def run_self_reflection(user_input: str, external_info: Optional[str] = None, history: Optional[list] = None) -> str:
    # 初始化固定 JSON 状态
    state_json: Dict[str, Any] = {
        "peripheral": {
            "user_input": user_input,
            "external_info": external_info or "",
            "history": history or []
        },
        "internal": {
            "iteration": 0,
            "compiled_knowledge": {
                "reasoning": "",
                "experience": "",
                "memory": ""
            },
            "think_output": "",
            "connect_output": "",
            "reflect_output": "",
            "final_answer": ""
        }
    }

    max_iter = MAX_ITERATIONS
    while state_json["internal"]["iteration"] < max_iter:
        # Ingest：编译三类知识（每次重试都重新编译，可携带历史反馈）
        try:
            knowledge = compile_knowledge(user_input, state_json["peripheral"]["external_info"])
        except Exception as e:
            logger.error(f"Knowledge compilation failed: {e}")
            knowledge = {"reasoning": "", "experience": "", "memory": ""}
        state_json["internal"]["compiled_knowledge"] = knowledge

        # 第一阶段：思考
        think_out = think_node(state_json)
        state_json["internal"]["think_output"] = think_out
        logger.info(f"Think: {think_out[:200]}...")

        # 第二阶段：连接
        connect_out = connect_node(state_json)
        state_json["internal"]["connect_output"] = connect_out
        logger.info(f"Connect: {connect_out[:200]}...")

        # 第三阶段：反思
        reflect_out = reflect_node(state_json)
        state_json["internal"]["reflect_output"] = reflect_out
        logger.info(f"Reflect: {reflect_out[:200]}...")

        # 第四阶段：输出
        final = output_node(state_json)
        state_json["internal"]["final_answer"] = final

        # 检查是否需要重新规划（例如输出中要求重新思考）
        if "重新思考" in final or "需要重新规划" in final:
            state_json["internal"]["iteration"] += 1
            logger.info(f"Replanning due to output instruction, iteration {state_json['internal']['iteration']}")
            continue
        else:
            break

    return state_json["internal"]["final_answer"]