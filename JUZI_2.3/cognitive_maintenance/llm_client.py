# llm_client.py
import os
import re
from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama
from config import ENHANCER_API_BASE, ENHANCER_API_KEY, LLM_TEMPERATURE
from logger_config import logger

# 原有全局 LLM（为维护工具在增强模式下使用，保留兼容）
default_llm = ChatOpenAI(
    model="JUZI",
    base_url=ENHANCER_API_BASE,
    api_key=ENHANCER_API_KEY,
    temperature=LLM_TEMPERATURE,
    request_timeout=120,
    max_retries=2
)

def create_llm(execution_mode: str = "enhanced", model_config: dict = None):
    """
    根据执行模式和模型配置创建 LLM 实例。
    execution_mode: 'enhanced' -> 调用增强层（model=JUZI）
                    'direct'   -> 直接调用底层 LLM
    model_config: dict with keys: type, model, api_base, api_key, temperature (仅 direct 需要)
    """
    if execution_mode == "enhanced":
        # 增强模式：调用增强层
        return ChatOpenAI(
            model="JUZI",
            base_url=ENHANCER_API_BASE,
            api_key=ENHANCER_API_KEY,
            temperature=LLM_TEMPERATURE,
            request_timeout=120,
            max_retries=2
        )
    else:  # direct mode
        if not model_config:
            raise ValueError("model_config is required for direct mode")
        if model_config.get("type") == "openai":
            return ChatOpenAI(
                model=model_config["model"],
                base_url=model_config["api_base"],
                api_key=model_config.get("api_key", "dummy"),
                temperature=model_config.get("temperature", LLM_TEMPERATURE),
                request_timeout=120,
                max_retries=2
            )
        else:  # ollama
            base_url = model_config.get("base_url") or model_config.get("api_base", "http://localhost:11434/v1")
            return ChatOllama(
                model=model_config["model"],
                base_url=base_url,
                temperature=model_config.get("temperature", LLM_TEMPERATURE),
                reasoning=False,
            )

def call_llm(prompt: str) -> str:
    """
    原有的直接调用方法，使用默认 LLM (增强模式，model=JUZI)
    保留以兼容可能未改动的旧代码。
    """
    try:
        from langchain_core.messages import HumanMessage
        response = default_llm.invoke([HumanMessage(content=prompt)])
        content = response.content.strip()
        code_block_pattern = r'```(?:json)?\s*\n?(.*?)\n?```'
        match = re.search(code_block_pattern, content, re.DOTALL)
        if match:
            content = match.group(1).strip()
        return content
    except Exception as e:
        logger.error(f"LLM 调用失败: {e}")
        return ""