import json
from typing import Dict, Any, Optional
from copy import deepcopy

from nodes import think_node, connect_node, reflect_node, output_node
from wiki_compiler import compile_knowledge
from config import MAX_ITERATIONS
from logger_config import logger
import asyncio
from concurrent.futures import ThreadPoolExecutor

_executor = ThreadPoolExecutor(max_workers=4)

def run_self_reflection(input_text: str, tools_text: str = "", llm=None) -> str:
    peripheral = {
        "input": input_text,
        "tools": tools_text,
        "llm": llm
    }
    state_json: Dict[str, Any] = {
        "peripheral": peripheral,
        "internal": {
            "iteration": 0,
            "think_knowledge": "",      # 新增
            "connect_knowledge": "",   # 新增
            "reflect_knowledge": "",   # 新增
            "think_output": "",
            "connect_output": "",
            "reflect_output": "",
            "final_answer": ""
        }
    }

    max_iter = MAX_ITERATIONS
    while state_json["internal"]["iteration"] < max_iter:
        user_query = _extract_last_user_query(input_text)

        # ==================== 1. think 阶段 ====================
        reasoning_text = compile_knowledge(user_query, categories=["reasoning"], llm=llm )
        state_json["internal"]["think_knowledge"] = reasoning_text
        think_out = think_node(state_json)
        state_json["internal"]["think_output"] = think_out
        logger.info(f"Think: {think_out[:1000]}...")

        # ==================== 2. connect 阶段 ====================
        connect_query = f"{user_query}\n初步思考：{think_out}" if think_out else user_query
        exp_mem_text = compile_knowledge(connect_query, categories=["experience", "memory"], llm=llm )
        state_json["internal"]["connect_knowledge"] = exp_mem_text
        connect_out = connect_node(state_json)
        state_json["internal"]["connect_output"] = connect_out
        logger.info(f"Connect: {connect_out[:1000]}...")

        # ==================== 3. reflect 阶段 ====================
        reflect_query = f"{user_query}\n方案：{connect_out}" if connect_out else user_query
        refl_text = compile_knowledge(reflect_query, categories=["reasoning", "experience"],llm=llm )
        state_json["internal"]["reflect_knowledge"] = refl_text
        reflect_out = reflect_node(state_json)
        state_json["internal"]["reflect_output"] = reflect_out
        logger.info(f"Reflect: {reflect_out[:1000]}...")

        # ==================== 4. output 阶段 ====================
        final = output_node(state_json)
        print(f"DEBUG: final = {final}")
        state_json["internal"]["final_answer"] = final

        if "重新规划" in final and state_json["internal"]["iteration"] + 1 < max_iter:
            state_json["internal"]["iteration"] += 1
            continue
        break

    return {
        "final_answer": state_json["internal"]["final_answer"],
        "thinking": {
            "think": state_json["internal"]["think_output"],
            "connect": state_json["internal"]["connect_output"],
            "reflect": state_json["internal"]["reflect_output"]
        }
    }


def _extract_last_user_query(input_text: str) -> str:
    """从 messages JSON 中提取最后一条用户消息内容（用于知识检索）"""
    try:
        messages = json.loads(input_text)
        for msg in reversed(messages):
            if msg.get("role") == "user":
                return msg.get("content", "")
    except:
        pass
    return ""

async def run_self_reflection_stages(input_text: str, tools_text: str = "", llm=None):
    """
    异步生成器，依次产生 (stage_name, content)
    stage_name: 'think', 'connect', 'reflect', 'output'
    """
    peripheral = {
        "input": input_text,
        "tools": tools_text,
        "llm": llm
    }
    state_json: Dict[str, Any] = {
        "peripheral": peripheral,
        "internal": {
            "iteration": 0,
            "think_knowledge": "",
            "connect_knowledge": "",
            "reflect_knowledge": "",
            "think_output": "",
            "connect_output": "",
            "reflect_output": "",
            "final_answer": ""
        }
    }

    max_iter = MAX_ITERATIONS
    while state_json["internal"]["iteration"] < max_iter:
        user_query = _extract_last_user_query(input_text)

        # ==================== 1. think 阶段 ====================
        # 将同步调用放到线程池
        reasoning_text = await asyncio.to_thread(compile_knowledge, user_query, categories=["reasoning"], llm=llm)
        state_json["internal"]["think_knowledge"] = reasoning_text
        think_out = await asyncio.to_thread(think_node, state_json)
        state_json["internal"]["think_output"] = think_out
        logger.info(f"Yielding think stage, length {len(think_out)}")
        yield ("think", think_out)
        logger.info("Think stage yielded")
        await asyncio.sleep(0)

        # ==================== 2. connect 阶段 ====================
        connect_query = f"{user_query}\n初步思考：{think_out}" if think_out else user_query
        exp_mem_text = await asyncio.to_thread(compile_knowledge, connect_query, categories=["experience", "memory"], llm=llm)
        state_json["internal"]["connect_knowledge"] = exp_mem_text
        connect_out = await asyncio.to_thread(connect_node, state_json)
        state_json["internal"]["connect_output"] = connect_out
        logger.info(f"Yielding connect stage, length {len(connect_out)}")
        yield ("connect", connect_out)
        logger.info("connect stage yielded")
        await asyncio.sleep(0)

        # ==================== 3. reflect 阶段 ====================
        reflect_query = f"{user_query}\n方案：{connect_out}" if connect_out else user_query
        refl_text = await asyncio.to_thread(compile_knowledge, reflect_query, categories=["reasoning", "experience"], llm=llm)
        state_json["internal"]["reflect_knowledge"] = refl_text
        reflect_out = await asyncio.to_thread(reflect_node, state_json)
        state_json["internal"]["reflect_output"] = reflect_out
        logger.info(f"Yielding reflect stage, length {len(reflect_out)}")
        yield ("reflect", reflect_out)
        logger.info("reflect stage yielded")
        await asyncio.sleep(0)

        # ==================== 4. output 阶段 ====================
        final = await asyncio.to_thread(output_node, state_json)
        state_json["internal"]["final_answer"] = final
        yield ("output", final)
        await asyncio.sleep(0)

        if "重新规划" in final and state_json["internal"]["iteration"] + 1 < max_iter:
            state_json["internal"]["iteration"] += 1
            continue
        break