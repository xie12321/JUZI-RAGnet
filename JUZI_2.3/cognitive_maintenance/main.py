# main.py
import argparse
from pathlib import Path
from typing import Dict, Optional, Callable

from tasks.ingest import ingest_conversation, extract_knowledge_from_conversation, precipitate_thought_pools
from tasks.classify import enhance_all_documents
from tasks.merge import merge_similar_docs
from tasks.summary import regenerate_summaries
from tasks.link import suggest_links_all, build_moc
from tasks.orphan import find_orphaned_pages
from llm_client import create_llm
from logger_config import logger
from config import get_wiki_root, REASONING_DIR, EXPERIENCE_DIR, MEMORY_DIR
import json
from datetime import datetime, timedelta


def _ensure_wiki_dirs():
    """确保知识库子目录存在"""
    root = get_wiki_root()
    for sub in [REASONING_DIR, EXPERIENCE_DIR, MEMORY_DIR, "ChatHistory"]:
        (root / sub).mkdir(parents=True, exist_ok=True)


def import_knowledge(text: str, llm):
    """将长文本析出知识并写入 Wiki，复用现有的提取逻辑。"""
    knowledge = extract_knowledge_from_conversation(text, llm=llm)
    result = ingest_conversation(text, llm=llm)
    return result


def run_health_check(
        mode: str = "incremental",
        execution_mode: str = "enhanced",
        model_config: Optional[Dict] = None,
        embed_model: str = "nomic-embed-text",
        progress_callback: Optional[Callable] = None
):
    """执行健康检查任务"""
    _ensure_wiki_dirs()
    force = (mode == "full")
    llm = create_llm(execution_mode=execution_mode, model_config=model_config)

    enhance_all_documents(llm, force=force, progress_callback=lambda c, t, msg:
        progress_callback and progress_callback("enhance_metadata", c, t, msg))
    if progress_callback:
        progress_callback("enhance_metadata", 0, 0, "阶段完成：增强文档元数据")

    regenerate_summaries(llm, force=force, progress_callback=lambda c, t, msg:
        progress_callback and progress_callback("regenerate_summaries", c, t, msg))
    if progress_callback:
        progress_callback("regenerate_summaries", 0, 0, "阶段完成：补充摘要")

    merge_similar_docs(llm, embed_model, force=force, progress_callback=lambda c, t, msg:
        progress_callback and progress_callback("merge", c, t, msg))
    if progress_callback:
        progress_callback("merge_similar_docs", 0, 0, "阶段完成：合并相似文档")

    suggest_links_all(llm, embed_model, progress_callback=lambda c, t, msg:
        progress_callback and progress_callback("link", c, t, msg))
    if progress_callback:
        progress_callback("suggest_links_all", 0, 0, "阶段完成：建议双链")

    if progress_callback:
        progress_callback("moc", 1, 1, "生成 MOC...")
    build_moc()

    if progress_callback:
        progress_callback("orphan", 1, 1, "检测孤立页面...")
    orphans = find_orphaned_pages()
    logger.info(f"孤立页面: {[p.name for p in orphans]}")
    if progress_callback:
        progress_callback("done", 1, 1, f"完成，孤立页面: {len(orphans)} 个")
    return orphans


def run_import_task(text: str, model_config: Dict, execution_mode: str, progress_callback=None):
    _ensure_wiki_dirs()
    llm = create_llm(execution_mode=execution_mode, model_config=model_config)
    return import_knowledge(text, llm)


def run_pool_precipitation(progress_callback=None):
    """沉淀暂存区思考池（委托给 ingest 模块）"""
    precipitate_thought_pools(progress_callback=progress_callback)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--all", action="store_true", help="执行全部健康检查")
    parser.add_argument("--scope", choices=["incremental", "full"], default="incremental", help="维护范围")
    args = parser.parse_args()
    if args.all:
        logger.info(f"开始全量健康检查 (模式: {args.scope})")
        run_health_check(mode=args.scope, execution_mode="enhanced")


if __name__ == "__main__":
    main()