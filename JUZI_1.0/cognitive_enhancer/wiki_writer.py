# wiki_writer.py
import time
import frontmatter
from pathlib import Path
from config import WIKI_ROOT, REASONING_DIR, EXPERIENCE_DIR, MEMORY_DIR
from logger_config import logger

def write_to_wiki(category: str, title: str, content: str, summary: str = "", tags: list = None):
    """将知识写入对应的 Wiki 目录"""
    if category == "reasoning":
        subdir = REASONING_DIR
    elif category == "experience":
        subdir = EXPERIENCE_DIR
    elif category == "memory":
        subdir = MEMORY_DIR
    else:
        raise ValueError("category must be reasoning/experience/memory")

    safe_title = title.replace("/", "_").replace(" ", "_")
    file_path = WIKI_ROOT / subdir / f"{safe_title}.md"
    file_path.parent.mkdir(parents=True, exist_ok=True)

    if file_path.exists():
        # 追加内容
        with open(file_path, 'r', encoding='utf-8') as f:
            existing = frontmatter.load(f)
        new_content = existing.content + f"\n\n## 补充\n{content}"
    else:
        existing = frontmatter.Post(content=content)
        new_content = content

    existing.content = new_content
    existing.metadata['title'] = title
    existing.metadata['summary'] = summary or content[:150]
    existing.metadata['tags'] = tags or []
    existing.metadata['updated'] = time.strftime("%Y-%m-%d")

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(frontmatter.dumps(existing))
    logger.info(f"Written to {category}: {title}")