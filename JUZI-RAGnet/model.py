# model.py
from langchain_ollama import ChatOllama, OllamaEmbeddings
from pydantic import BaseModel, Field
from typing import List, Dict, Any

from config import LLM_MODEL, EMBED_MODEL

# 基础 LLM
llm = ChatOllama(model=LLM_MODEL, temperature=0.7)
embeddings = OllamaEmbeddings(model=EMBED_MODEL)

# 结构化输出模型定义
class PlanStep(BaseModel):
    tool: str = Field(description="工具名称")
    params: Dict[str, Any] = Field(description="工具参数")
    depends_on: Dict[str, str] | None = Field(
        default=None,
        description="参数依赖映射，键为当前步骤的参数名，值为前一步输出的字段名（格式：step_X.field 或 tool_name.field）"
    )

class Plan(BaseModel):
    steps: List[PlanStep] = Field(description="执行步骤列表")

class VerificationResult(BaseModel):
    passed: bool = Field(description="是否通过验证")
    feedback: str = Field(description="反馈信息")

# 结构化 LLM
structured_llm = llm.with_structured_output(Plan)
verification_structured_llm = llm.with_structured_output(VerificationResult)