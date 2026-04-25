# wiki_reader.py
import frontmatter
from pathlib import Path
from typing import List, Dict, Optional
from config import WIKI_ROOT, REASONING_DIR, EXPERIENCE_DIR, MEMORY_DIR
from logger_config import logger
from wiki_data import _doc_cache, _graph, _reverse_graph   # 新增
from wiki_retriever import get_retriever

# 注意：不再定义 _graph, _reverse_graph, _doc_cache

def _get_category(path: Path) -> str:
    if REASONING_DIR in path.parts:
        return "reasoning"
    elif EXPERIENCE_DIR in path.parts:
        return "experience"
    elif MEMORY_DIR in path.parts:
        return "memory"
    else:
        return "other"

def _load_all_docs():
    """加载所有文档到 _doc_cache"""
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

def build_index():
    _load_all_docs()
    # 同时构建图结构（需要调用 build_graph，该函数在 wiki_graph.py 中定义）
    from wiki_graph import build_graph
    build_graph()
    logger.info(f"Loaded {len(_doc_cache)} documents, graph built")

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
    """使用图谱增强的混合检索（推荐）"""
    from wiki_retriever import get_retriever
    retriever = get_retriever(rebuild=True)
    results = retriever.hybrid_search_with_graph(query, top_k=top_k * 2, expand_neighbors=True)

    if category:
        results = [r for r in results if category in str(r['metadata'].get('source', ''))]

    converted = []
    for r in results[:top_k]:
        # 尝试从 metadata 中获取 title 和 summary
        title = r['metadata'].get('title', '')
        summary = r['metadata'].get('summary', '')
        # 如果 metadata 中没有，则从 _doc_cache 中查找
        if not title or not summary:
            source_path = r['metadata'].get('source')
            if source_path:
                from pathlib import Path
                source_path = Path(source_path)
                doc = _doc_cache.get(source_path)
                if doc:
                    title = doc.get('title', title)
                    summary = doc.get('summary', summary)
        # 确保至少有一个默认值
        if not title:
            title = "未知文档"
        converted.append({
            'title': title,
            'summary': summary,
            'content': r['content'],
            'metadata': r['metadata'],
            'score': r.get('score', 0)
        })
    return converted

def get_full_content(doc: Dict) -> str:
    return doc['content']

def hybrid_retrieve(query: str, category: str = None, top_k: int = 5) -> List[Dict]:
    """混合检索接口（仅向量+BM25，不包含图谱扩展）"""
    retriever = get_retriever()
    results = retriever.hybrid_search(query, top_k=top_k * 2)
    # 按 category 过滤...
    filtered = []
    for res in results:
        if category:
            cat_match = False
            if 'category' in res['metadata'] and res['metadata']['category'] == category:
                cat_match = True
            elif 'tags' in res['metadata'] and category in res['metadata']['tags']:
                cat_match = True
            elif 'source' in res['metadata'] and category in res['metadata']['source']:
                cat_match = True
            if not cat_match:
                continue
        filtered.append(res)
        if len(filtered) >= top_k:
            break
    output = []
    for res in filtered:
        source_path = res['metadata'].get('source')
        summary = ""
        title = res['metadata'].get('title', "")
        if source_path:
            try:
                import frontmatter
                with open(source_path, 'r', encoding='utf-8') as f:
                    post = frontmatter.load(f)
                summary = post.metadata.get('summary', '')
                if not title:
                    title = post.metadata.get('title', Path(source_path).stem)
            except:
                pass
        output.append({
            'title': title,
            'summary': summary,
            'content': res['content'],
            'metadata': res['metadata'],
            'score': res['score']
        })
    return output

def find_doc_by_title(title: str) -> Optional[Path]:
    """通过标题查找文档路径"""
    for path, doc in _doc_cache.items():
        if doc.get('title') == title:
            return path
    return None