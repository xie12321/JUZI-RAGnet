import frontmatter
from pathlib import Path
from typing import List, Dict
from config import WIKI_ROOT, USE_EMBEDDING, EMBED_MODEL, REASONING_DIR, EXPERIENCE_DIR, MEMORY_DIR
from logger_config import logger

_doc_cache: Dict[Path, Dict] = {}

def _load_all_docs():
    global _doc_cache
    _doc_cache.clear()
    for md_file in WIKI_ROOT.rglob("*.md"):
        if '.obsidian' in md_file.parts:
            continue
        try:
            with open(md_file, 'r', encoding='utf-8') as f:
                post = frontmatter.load(f)
            _doc_cache[md_file] = {
                'path': md_file,
                'title': post.metadata.get('title', md_file.stem),
                'summary': post.metadata.get('summary', ''),
                'tags': post.metadata.get('tags', []),
                'category': _get_category(md_file),
                'content': post.content
            }
        except Exception as e:
            logger.error(f"Failed to load {md_file}: {e}")

def _get_category(path: Path) -> str:
    if REASONING_DIR in path.parts:
        return "reasoning"
    elif EXPERIENCE_DIR in path.parts:
        return "experience"
    elif MEMORY_DIR in path.parts:
        return "memory"
    else:
        return "other"

def build_index():
    _load_all_docs()
    logger.info(f"Loaded {len(_doc_cache)} documents")

def retrieve_by_keywords(query: str, category: str = None, top_k: int = 5) -> List[Dict]:
    query_lower = query.lower()
    scored = []
    for doc in _doc_cache.values():
        if category and doc['category'] != category:
            continue
        text = (doc['title'] + " " + doc['summary'] + " " + " ".join(doc['tags'])).lower()
        score = sum(1 for word in query_lower.split() if word in text)
        if score > 0:
            scored.append((score, doc))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [doc for score, doc in scored[:top_k]]

def retrieve(query: str, category: str = None, top_k: int = 5) -> List[Dict]:
    return retrieve_by_keywords(query, category, top_k)

def get_full_content(doc: Dict) -> str:
    return doc['content']