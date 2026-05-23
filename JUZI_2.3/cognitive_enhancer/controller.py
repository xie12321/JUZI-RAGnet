# controller.py
import json
from typing import Dict, Any, Optional

from langchain_core.messages import HumanMessage
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI

from nodes import think_node, connect_node, reflect_node, output_node, output_node_plain
from config import MAX_ITERATIONS, get_wiki_root
from logger_config import logger
import asyncio
from concurrent.futures import ThreadPoolExecutor

from thought_pool import ThoughtPool, ThoughtPoolLLM
from thought_pool_cache import ThoughtPoolCache
from wiki_retriever import get_retriever

# 新增导入
from system_prompt import get_identity_llm

_executor = ThreadPoolExecutor(max_workers=4)


def create_zero_temp_llm(llm):
    """
    基于现有 LLM 实例创建一个温度为零的新实例，用于精确的判断。
    兼容 ChatOpenAI 和 ChatOllama，若类型未知则回退到原实例。
    已修改为属性检测，避免包装器导致 isinstance 失效。
    """
    # 如果传入的是包装后的 IdentityLLM（RunnableSequence），尝试从中取出原始 LLM
    if hasattr(llm, 'base_llm'):
        llm = llm.base_llm
    elif hasattr(llm, 'last') and hasattr(llm.last, 'base_llm'):
        # 某些 Runnable 组合方式，尝试深入
        llm = llm.last.base_llm

    # 用属性判断代替 isinstance
    if hasattr(llm, 'model_name') and hasattr(llm, 'openai_api_base'):
        # ChatOpenAI 的特征
        return ChatOpenAI(
            model=llm.model_name,
            base_url=llm.openai_api_base,
            api_key=llm.openai_api_key,
            temperature=0,
            max_tokens=10
        )
    elif hasattr(llm, 'model') and hasattr(llm, 'base_url'):
        # ChatOllama 的特征
        return ChatOllama(
            model=llm.model,
            base_url=llm.base_url,
            temperature=0,
            reasoning=False
        )
    else:
        # 回退
        return llm


def is_simple_query(llm, user_query: str,  context: str = "") -> bool:
    """判断用户问题是否为简单问题（无需深度推理）"""
    judge_llm = create_zero_temp_llm(llm)
    # 注入轻量身份
    judge_llm = get_identity_llm(judge_llm, mode="lite")
    prompt = f"""判断以下用户问题是否属于简单问题。简单问题的定义：
- 日常问候（如"你好"、"早上好"）
- 简单事实询问（如"今天星期几"、"1+1等于几"）
- 不需要深度推理、不需要调用外部工具即可立即回答

如果属于简单问题，回答"是"；否则回答"否"。只输出一个字。

【外部输入】（包含完整的对话历史，JSON格式，包含user/assistant/system/tool等消息）：
{context}

用户问题：
{user_query}

判断："""
    response = judge_llm.invoke([HumanMessage(content=prompt)])
    return response.content.strip() == "是"


def simple_output(llm, user_query: str, tools_def: str = "", context: str = "") -> str:
    """对简单问题直接生成回答，一次性调用 LLM 不经过循环"""
    # 这里的 llm 已经是包装后的 cognitive_llm，所以直接使用即可
    prompt = f"""请直接、简洁和友善地回答以下问题。不需要展开解释，也不需要使用工具。
【外部输入】（包含完整的对话历史，JSON格式，包含user/assistant/system/tool等消息）：
{context}

用户问题：
{user_query}

回答："""
    response = llm.invoke([HumanMessage(content=prompt)])
    return response.content


def judge_pool_ready(llm, pool_content: str, user_query: str, stage: str = "最终") -> bool:
    """
    判断思考池当前状态是否已经足够生成最终答案。
    stage: "中间" 或 "最终"，影响判断的严格程度。
    """
    judge_llm = create_zero_temp_llm(llm)
    # 注入轻量身份
    judge_llm = get_identity_llm(judge_llm, mode="lite")

    if stage == "中间":
        strictness = """**判断标准（中间阶段，请偏向于"是"）：**
- 如果思考池中已包含可以直接回答用户问题的内容，或者问题本身非常简单，请回答"是"
- 只有当前思考池明显无法支撑回答、存在严重逻辑矛盾、或需要更多步骤才能解决问题时，才回答"否"
- 对于算术题、事实查询、简单问候、翻译等不需要多步推理的问题，一律回答"是" """
    else:
        strictness = """**需要重新规划的情况（回答"是"）：**
- 思考池中存在无法调和的明显逻辑矛盾
- 完成核心任务所必需的关键信息仍然缺失
- 存在会导致方案完全失效的边界情况未被处理

**不需要重新规划的情况（回答"否"）：**
- 思考池内容已完整、自洽，能够支撑最终回答
- 虽然可能还有一些小的表达瑕疵，但可以在生成最终答案时自然修正"""

    prompt = f"""你现在处于【{'中间' if stage == '中间' else '最终'}决策】阶段。

请仔细阅读以下思考池的全部内容，判断当前认知状态是否已足够高质量，可以直接生成最终答案。

{strictness}

思考池完整内容：
{pool_content[:2000]}

用户原始问题：
{user_query}

请直接回答"是"或"否"，不要添加任何其他内容。"""
    response = judge_llm.invoke([HumanMessage(content=prompt)])
    return response.content.strip() == "是"


def run_self_reflection(input_text: str, tools_text: str = "", llm=None) -> dict:
    """同步版本的自省循环"""
    # 注入完整认知人格，包装为 cognitive_llm
    cognitive_llm = get_identity_llm(llm, mode="full")

    peripheral = {
        "input": input_text,
        "tools": tools_text,
        "llm": cognitive_llm   # 后续所有节点均使用此实例
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
            "final_answer": "",
            "final_context": ""
        }
    }

    user_query = _extract_last_user_query(input_text)
    retriever = get_retriever()
    tools_def = state_json["peripheral"].get("tools", "")

    # 创建零温LLM实例，用于缓存匹配和判断
    zero_temp_llm = create_zero_temp_llm(cognitive_llm)

    # ================= 难度评估 =================
    if is_simple_query(cognitive_llm, user_query, input_text):
        final = simple_output(cognitive_llm, user_query, input_text, tools_def)
        return {
            "final_answer": final,
            "thinking": {
                "think": "", "connect": "", "reflect": ""
            }
        }

    # ================= 暂存区查询 =================
    cache_dir = str(get_wiki_root() / ".thought_pool_drafts")
    cache = ThoughtPoolCache(judge_llm=get_identity_llm(zero_temp_llm, mode="lite"),
                             cache_dir=cache_dir)
    cached = cache.find_best_match(user_query)
    # pool_llm 内部会创建零温 LLM，但我们在 ThoughtPoolLLM 中也会包装，所以这里正常传入 cognitive_llm
    pool_llm = ThoughtPoolLLM(cognitive_llm, retriever, tools_def)

    if cached:
        pool = ThoughtPool(user_query)
        pool.content = cached["pool_content"]

        reflect_context = pool.get_context()
        state_json["internal"]["reflect_knowledge"] = reflect_context
        reflect_out = reflect_node(state_json)
        pool_llm.process_node_output(pool, "reflect", reflect_out,
                                     search_categories=["reasoning", "experience"], context=input_text)

        need_replan = judge_pool_ready(cognitive_llm, pool.get_context(), user_query, stage="最终")
        if not need_replan:
            final = output_node(state_json)
            state_json["internal"]["final_answer"] = final
            cache.save(pool.content, user_query)
            return {
                "final_answer": final,
                "thinking": {
                    "think": state_json["internal"]["think_output"],
                    "connect": state_json["internal"]["connect_output"],
                    "reflect": state_json["internal"]["reflect_output"]
                }
            }
        # 需要完整自省，但思考池已具备初始内容，跳过初始化
    else:
        pool = ThoughtPool(user_query)
        pool_llm.initialize_pool(pool, context=input_text)

    # ================= 标准自省循环 =================
    max_iter = MAX_ITERATIONS
    while state_json["internal"]["iteration"] < max_iter:
        orig_user_query = _extract_last_user_query(input_text)
        user_query = orig_user_query

        # ====== 1. think ======
        think_context = pool.get_context()
        state_json["internal"]["think_knowledge"] = think_context
        think_out = think_node(state_json)
        state_json["internal"]["think_output"] = think_out
        logger.info(f"Think: {think_out[:1000]}...")
        pool_llm.process_node_output(pool, "think", think_out, search_categories=["reasoning"], context=input_text)

        if judge_pool_ready(cognitive_llm, pool.get_context(), orig_user_query, stage="中间"):
            state_json["internal"]["final_context"] = pool.get_context()
            final = output_node(state_json)
            state_json["internal"]["final_answer"] = final
            cache.save(pool.content, orig_user_query)
            return {
                "final_answer": final,
                "thinking": {
                    "think": think_out,
                    "connect": "",
                    "reflect": ""
                }
            }

        # ====== 2. connect ======
        connect_context = pool.get_context()
        state_json["internal"]["connect_knowledge"] = connect_context
        connect_out = connect_node(state_json)
        state_json["internal"]["connect_output"] = connect_out
        logger.info(f"Connect: {connect_out[:1000]}...")
        pool_llm.process_node_output(pool, "connect", connect_out, search_categories=["experience", "memory"], context=input_text)

        if judge_pool_ready(cognitive_llm, pool.get_context(), orig_user_query, stage="中间"):
            state_json["internal"]["final_context"] = pool.get_context()
            final = output_node(state_json)
            state_json["internal"]["final_answer"] = final
            cache.save(pool.content, orig_user_query)
            return {
                "final_answer": final,
                "thinking": {
                    "think": think_out,
                    "connect": connect_out,
                    "reflect": ""
                }
            }

        # ====== 3. reflect ======
        reflect_context = pool.get_context()
        state_json["internal"]["reflect_knowledge"] = reflect_context
        reflect_out = reflect_node(state_json)
        state_json["internal"]["reflect_output"] = reflect_out
        logger.info(f"Reflect: {reflect_out[:1000]}...")
        pool_llm.process_node_output(pool, "reflect", reflect_out,
                                     search_categories=["reasoning", "experience"], context=input_text)

        need_replan = judge_pool_ready(cognitive_llm, pool.get_context(), orig_user_query, stage="最终")
        logger.info(f"判断节点结果: 是否需要重新规划 -> {need_replan}")

        if need_replan and state_json["internal"]["iteration"] + 1 < max_iter:
            state_json["internal"]["previous_reflection"] = reflect_out
            state_json["internal"]["iteration"] += 1
            pool_llm.supplement_for_replan(pool, reflect_out, orig_user_query, context=input_text)
            continue
        else:
            state_json["internal"]["previous_reflection"] = ""
            state_json["internal"]["final_context"] = pool.get_context()
            final = output_node(state_json)
            state_json["internal"]["final_answer"] = final
            cache.save(pool.content, orig_user_query)
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


async def run_self_reflection_stages(input_text: str, tools_text: str = "", llm=None, pool_update_callback=None):
    """
    异步生成器，依次产生 (stage_name, content)
    若提供了 pool_update_callback，每次思考池更新后会调用该回调，传入最新的池内容
    """
    # 注入完整认知人格
    cognitive_llm = get_identity_llm(llm, mode="full")

    peripheral = {
        "input": input_text,
        "tools": tools_text,
        "llm": cognitive_llm
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

    user_query = _extract_last_user_query(input_text)
    retriever = get_retriever()
    tools_def = state_json["peripheral"].get("tools", "")

    zero_temp_llm = create_zero_temp_llm(cognitive_llm)

    if is_simple_query(cognitive_llm, user_query,  context=input_text):
        final = simple_output(cognitive_llm, user_query, context=input_text, tools_def=tools_def)
        yield ("output", final)
        return

    cache_dir = str(get_wiki_root() / ".thought_pool_drafts")
    cache = ThoughtPoolCache(judge_llm=get_identity_llm(zero_temp_llm, mode="lite"),
                             cache_dir=cache_dir)
    cached = cache.find_best_match(user_query)
    pool_llm = ThoughtPoolLLM(cognitive_llm, retriever, tools_def)

    if cached:
        pool = ThoughtPool(user_query)
        pool.content = cached["pool_content"]

        reflect_context = pool.get_context()
        state_json["internal"]["reflect_knowledge"] = reflect_context
        reflect_out = await asyncio.to_thread(reflect_node, state_json)
        await asyncio.to_thread(pool_llm.process_node_output, pool, "reflect", reflect_out,
                                search_categories=["reasoning", "experience"], context=input_text)
        if pool_update_callback:
            await pool_update_callback(pool.get_context())

        need_replan = await asyncio.to_thread(judge_pool_ready, cognitive_llm, pool.get_context(), user_query, "最终")
        if not need_replan:
            final = output_node_plain(state_json)
            state_json["internal"]["final_answer"] = final
            await asyncio.to_thread(cache.save, pool.content, user_query)
            yield ("output", final)
            return
    else:
        pool = ThoughtPool(user_query)
        await asyncio.to_thread(pool_llm.initialize_pool, pool, input_text)
        if pool_update_callback:
            await pool_update_callback(pool.get_context())

    max_iter = MAX_ITERATIONS
    while state_json["internal"]["iteration"] < max_iter:
        orig_user_query = _extract_last_user_query(input_text)
        user_query = orig_user_query

        # 1. think
        think_context = pool.get_context()
        state_json["internal"]["think_knowledge"] = think_context
        think_out = await asyncio.to_thread(think_node, state_json)
        state_json["internal"]["think_output"] = think_out
        logger.info(f"Yielding think stage, length {len(think_out)}")
        yield ("think", think_out)
        await asyncio.to_thread(pool_llm.process_node_output, pool, "think", think_out, ["reasoning"], context=input_text)
        if pool_update_callback:
            await pool_update_callback(pool.get_context())
        await asyncio.sleep(0)

        if await asyncio.to_thread(judge_pool_ready, cognitive_llm, pool.get_context(), orig_user_query, "中间"):
            state_json["internal"]["final_context"] = pool.get_context()
            final = await asyncio.to_thread(output_node_plain, state_json)
            state_json["internal"]["final_answer"] = final
            yield ("output", final)
            await asyncio.to_thread(cache.save, pool.content, orig_user_query)
            return

        # 2. connect
        connect_context = pool.get_context()
        state_json["internal"]["connect_knowledge"] = connect_context
        connect_out = await asyncio.to_thread(connect_node, state_json)
        state_json["internal"]["connect_output"] = connect_out
        logger.info(f"Yielding connect stage, length {len(connect_out)}")
        yield ("connect", connect_out)
        await asyncio.to_thread(pool_llm.process_node_output, pool, "connect", connect_out, ["experience", "memory"], context=input_text)
        if pool_update_callback:
            await pool_update_callback(pool.get_context())
        await asyncio.sleep(0)

        if await asyncio.to_thread(judge_pool_ready, cognitive_llm, pool.get_context(), orig_user_query, "中间"):
            state_json["internal"]["final_context"] = pool.get_context()
            final = await asyncio.to_thread(output_node_plain, state_json)
            state_json["internal"]["final_answer"] = final
            yield ("output", final)
            await asyncio.to_thread(cache.save, pool.content, orig_user_query)
            return

        # 3. reflect
        reflect_context = pool.get_context()
        state_json["internal"]["reflect_knowledge"] = reflect_context
        reflect_out = await asyncio.to_thread(reflect_node, state_json)
        state_json["internal"]["reflect_output"] = reflect_out
        logger.info(f"Yielding reflect stage, length {len(reflect_out)}")
        yield ("reflect", reflect_out)
        await asyncio.to_thread(pool_llm.process_node_output, pool, "reflect", reflect_out,
                                ["reasoning", "experience"], context=input_text)
        if pool_update_callback:
            await pool_update_callback(pool.get_context())
        await asyncio.sleep(0)

        need_replan = await asyncio.to_thread(judge_pool_ready, cognitive_llm, pool.get_context(), orig_user_query, "最终")
        logger.info(f"判断节点结果: 是否需要重新规划 -> {need_replan}")

        if need_replan and state_json["internal"]["iteration"] + 1 < max_iter:
            state_json["internal"]["previous_reflection"] = reflect_out
            state_json["internal"]["iteration"] += 1
            yield ("reset_thinking", "")
            await asyncio.to_thread(pool_llm.supplement_for_replan, pool, reflect_out, orig_user_query, input_text)
            if pool_update_callback:
                await pool_update_callback(pool.get_context())
            continue
        else:
            state_json["internal"]["previous_reflection"] = ""
            state_json["internal"]["final_context"] = pool.get_context()
            final = await asyncio.to_thread(output_node_plain, state_json)
            state_json["internal"]["final_answer"] = final
            yield ("output", final)
            await asyncio.to_thread(cache.save, pool.content, orig_user_query)
            await asyncio.sleep(0)
            break