# thought_pool.py
from typing import List, Optional
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama
from logger_config import logger
from system_prompt import get_identity_llm


def create_zero_temp_llm(llm):
    """
    基于现有 LLM 实例创建一个温度为零的新实例，用于精确的判断。
    已修改为属性检测，避免包装器导致 isinstance 失效。
    """
    # 如果传入的是包装后的 IdentityLLM，尝试取出原始 LLM
    if hasattr(llm, 'base_llm'):
        llm = llm.base_llm
    elif hasattr(llm, 'last') and hasattr(llm.last, 'base_llm'):
        llm = llm.last.base_llm

    if hasattr(llm, 'model_name') and hasattr(llm, 'openai_api_base'):
        return ChatOpenAI(
            model=llm.model_name,
            base_url=llm.openai_api_base,
            api_key=llm.openai_api_key,
            temperature=0,
        )
    elif hasattr(llm, 'model') and hasattr(llm, 'base_url'):
        return ChatOllama(
            model=llm.model,
            base_url=llm.base_url,
            temperature=0,
            reasoning=False
        )
    else:
        return llm


class ThoughtPool:
    """纯文本思考池：由 LLM 全权维护的认知容器"""
    def __init__(self, user_query: str):
        self.content: str = f"用户问题：{user_query}\n\n"
        self.user_query = user_query

    def get_context(self) -> str:
        return self.content


class ThoughtPoolLLM:
    """思考池调度中心：主动检索、融合重写，维护思考池"""
    def __init__(self, llm, retriever, tools_def: str = ""):
        # 这里接收的 llm 已经是 cognitive_llm，无需再次包装
        self.llm = llm
        self.retriever = retriever
        self.tools_def = tools_def

    # ========== 初始化思考池（纯动态启动） ==========
    def initialize_pool(self, pool: ThoughtPool, context: str = ""):
        """
        首次检索全库知识，并生成初始思考池内容。
        核心推理框架已外置到 system_prompt，不再注入思考池。
        """
        query = pool.content
        results = self.retriever.hybrid_search_with_graph(
            query, categories=None, top_k=10, expand_neighbors=False
        )
        if not results:
            # 无检索结果时，生成第一版自语草稿
            prompt = f"""这是一切思考尚未开始时的准备——所有相关的信息刚刚被自动激活，尚未经过有意识的梳理。

请像在脑海中无意识地消化信息一样，用第一人称"我"将这些涌入脑海的碎片记录下来：
- 用户的问题像一颗石子投入水面，激起了哪些联想？
- 检索到的知识中，有哪些似乎与这个问题隐隐相关？
- 有没有什么概念、背景、或关键词，在你还没来得及仔细思考时就自然浮现了出来？

不需要组织、不需要结论、不需要结构。就让这些念头像水面上泛起的涟漪，自由地散开。

用户当前问题：
{query}

外部输入（包含完整的对话历史，JSON格式，包含user/assistant/system/tool等消息）：
{context}

检索到的相关知识：
{knowledge_text}

我脑海中浮现出的碎片："""
            response = self.llm.invoke([HumanMessage(content=prompt)])
            pool.content = response.content
            return

        knowledge_text = "\n".join([
            f"- {r['content']}（来源：{r['metadata'].get('title', '未知')}）"
            for r in results
        ])
        # 使用自语式重写进行初始融合
        self._rewrite_pool(pool, "初始化", "", [r['content'] for r in results], context=context)

    # ========== Skills 推荐与分模式检索 ==========
    def _recommend_skills(self, node_output: str, search_categories: Optional[List[str]] = None) -> List[str]:
        """基于节点输出的检索指导，推荐需要加载的 Skill 文档标题（仅推理库/记忆库）"""
        if not search_categories or not ('reasoning' in search_categories or 'memory' in search_categories):
            return []

        skill_titles = self.retriever.get_all_skill_titles()
        if not skill_titles:
            return []

        skill_list_str = "\n".join([f"- {t}" for t in skill_titles])
        prompt = f"""你正在为一个知识推理任务选择需要的思维工具。

当前节点的检索指导：
{node_output[:3000]}

可用的思维工具（Skill 文档）列表：
{skill_list_str}

请根据当前节点的检索指导，选择1~3个最需要加载的 Skill 文档。只输出文档标题，每行一个。
如果当前检索指导已足够明确，不需要额外 Skill，请输出"无需加载"。

需要的 Skill 标题（或"无需加载"）："""
        llm_zero = create_zero_temp_llm(self.llm)
        # 注入完整人格（这个任务仍是认知的一部分）
        llm_zero = get_identity_llm(llm_zero, mode="full")
        response = llm_zero.invoke([HumanMessage(content=prompt)])
        text = response.content.strip()
        if text == "无需加载":
            return []
        selected = [line.strip() for line in text.split('\n') if line.strip()]
        return selected[:3]

    def process_node_output(self, pool: ThoughtPool, stage: str, node_output: str,
                            search_categories: Optional[List[str]] = None, context: str = "",
                            inject_node_output: bool = True):
        """
        处理自省循环节点输出：
        1. 对于推理库和记忆库：通过 Skills 推荐加载对应的 Skill 文档
        2. 对于经验库：使用关键词混合检索
        3. 将节点输出与新检索到的知识一起注入思考池，触发自语式重写
        节点输出始终参与融合（不再依赖 inject_node_output 标记的默认值）。
        """
        # 1. Skills 推荐与加载
        skills_docs = []
        need_skills = search_categories and ('reasoning' in search_categories or 'memory' in search_categories)

        if need_skills:
            skill_titles = self._recommend_skills(node_output, search_categories)
            for title in skill_titles:
                doc_content = self.retriever.get_document_by_title(title)
                if doc_content:
                    skills_docs.append(doc_content[:2000])
                    logger.info(f"滑动窗口加载 Skill: {title}")

        # 2. 经验库关键词检索
        exp_docs = []
        need_exp = search_categories and 'experience' in search_categories
        if need_exp:
            keywords = self._extract_keywords(node_output)
            for kw in keywords:
                results = self.retriever.hybrid_search_with_graph(
                    kw, categories=["experience"], top_k=3, expand_neighbors=False
                )
                for r in results:
                    exp_docs.append(r['content'])

        # 3. 融合重写：节点输出始终参与，不再依赖条件判断
        all_new_knowledge = skills_docs + exp_docs
        self._rewrite_pool(pool, f"{stage}_知识注入", node_output, all_new_knowledge, context=context)

    def supplement_for_replan(self, pool: ThoughtPool, reflect_out: str, user_query: str, context: str = ""):
        """重新规划时补充检索并重写思考池"""
        query = f"{user_query}\n{reflect_out}"
        results = self.retriever.hybrid_search_with_graph(
            query, categories=None, top_k=10, expand_neighbors=False
        )
        new_knowledge = [r['content'] for r in results]
        self._rewrite_pool(pool, "replan", reflect_out, new_knowledge, context=context)

    def _extract_keywords(self, text: str) -> List[str]:
        """从文本中提取1~3个最核心的关键词，用于知识库检索"""
        key_llm = create_zero_temp_llm(self.llm)
        # 注入完整人格
        key_llm = get_identity_llm(key_llm, mode="full")
        prompt = f"""从以下文本中提取1~3个最核心的关键词或短句，用于知识库检索。只输出关键词，每行一个。

文本：
{text[:5000]}

关键词："""
        response = key_llm.invoke([HumanMessage(content=prompt)])
        keywords = [line.strip() for line in response.content.strip().split('\n') if line.strip()]
        return keywords[:3]

    # ========== 思考池重写：产出连贯的第一人称自语笔记 ==========
    def _rewrite_pool(self, pool: ThoughtPool, stage: str, node_output: str,
                      new_knowledge: List[str], context: str = ""):
        """重写思考池：以第一人称自语的方式更新工作笔记"""
        pool_llm = create_zero_temp_llm(self.llm)
        pool_llm = get_identity_llm(pool_llm, mode="full")

        knowledge_str = "\n".join(new_knowledge) if new_knowledge else "（无新信息）"

        if node_output:
            new_think_section = f"""
我刚刚产生的阶段性思考（来自{stage}阶段）：
{node_output}
"""
        else:
            new_think_section = ""

        prompt = f"""你现在是以第一人称"我"进行思考的 系统智能体“橘子”。你正在持续更新你的工作笔记。

请根据以下材料，以连贯自然的口语化段落，写出你最新的思考草稿。这份草稿应该像你此刻在脑中的自言自语，而不是一份整理好的报告。

要求：
- 全程使用"我"的视角，就像在对自己说话。自然点的开头如"用户问了……这让我想到……"，中途可以自由转折如"等等，如果考虑……"、"还有个角度是……"。
- 不要使用任何序号、列表或表格。如果有多个要点，用自然的过渡句带出来。
- 灵活使用思考标记：不确定时用〖待核实〗，有依据时用〖已核实〗。
- 遇到矛盾或疑问，直接在行文中说出来："但这和之前……似乎矛盾，我需要再查一下。"
- 保持草稿的流畅性，可以像说话一样有停顿、有转折，不要写成论文。

用户问题：
{pool.user_query}

你之前的思考笔记：
{pool.content}
{new_think_section}
新检索/注入的信息：
{knowledge_str}

外部输入（包含完整的对话历史，JSON格式，包含user/assistant/system/tool等消息）：
{context}

可用工具：
{self.tools_def if self.tools_def else "无"}

请以"我"开头，写出你更新后的完整思考笔记："""
        response = pool_llm.invoke([HumanMessage(content=prompt)])
        pool.content = response.content