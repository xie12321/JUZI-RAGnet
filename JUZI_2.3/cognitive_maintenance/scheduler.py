from apscheduler.schedulers.background import BackgroundScheduler
from tasks.classify import enhance_all_documents
from tasks.merge import merge_similar_docs
from tasks.summary import regenerate_summaries
from tasks.link import suggest_links_all, build_moc
from tasks.orphan import find_orphaned_pages
from logger_config import logger

scheduler = BackgroundScheduler()

def run_full_check():
    logger.info("开始执行健康检查...")
    enhance_all_documents()
    merge_similar_docs()
    regenerate_summaries()
    suggest_links_all()
    build_moc()
    orphans = find_orphaned_pages()
    logger.info(f"孤立页面: {len(orphans)}")

scheduler.add_job(run_full_check, 'cron', hour=3, minute=0)
scheduler.start()