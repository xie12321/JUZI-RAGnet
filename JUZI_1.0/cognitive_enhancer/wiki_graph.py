# wiki_graph.py
import re
import networkx as nx
from pathlib import Path
from typing import List, Dict, Set, Optional
from collections import defaultdict

from config import WIKI_ROOT
from logger_config import logger
from wiki_data import _doc_cache, _graph, _reverse_graph

# 全局 NetworkX 图（用于 PageRank）
_nx_graph = None
_pagerank = None

# ---------- 图构建 ----------
def _resolve_link(link_target: str, current_file: Path) -> Optional[Path]:
    """解析双链目标为绝对路径"""
    if not link_target.endswith('.md'):
        link_target += '.md'
    if link_target.startswith('/'):
        candidate = WIKI_ROOT / link_target[1:]
        return candidate if candidate.exists() else None
    candidate = current_file.parent / link_target
    if candidate.exists():
        return candidate
    for found in WIKI_ROOT.rglob(link_target):
        if '.obsidian' not in found.parts:
            return found
    return None

def build_graph():
    """构建双链图，填充 _graph 和 _reverse_graph"""
    global _graph, _reverse_graph
    _graph.clear()
    _reverse_graph.clear()
    all_md_files = [p for p in WIKI_ROOT.rglob("*.md") if '.obsidian' not in p.parts]
    for doc_path in all_md_files:
        try:
            with open(doc_path, 'r', encoding='utf-8') as f:
                content = f.read()
            links = re.findall(r'\[\[([^\]|#]+)', content)
            for target in links:
                target_path = _resolve_link(target.strip(), doc_path)
                if target_path and target_path in all_md_files:
                    _graph[doc_path].add(target_path)
                    _reverse_graph[target_path].add(doc_path)
        except Exception as e:
            logger.error(f"Failed to parse {doc_path}: {e}")
    logger.info(f"Graph built: {len(_graph)} nodes, {sum(len(v) for v in _graph.values())} edges")

def build_nx_graph() -> nx.DiGraph:
    """从 _graph 构建 NetworkX 有向图"""
    global _nx_graph
    G = nx.DiGraph()
    for src, tgts in _graph.items():
        for tgt in tgts:
            G.add_edge(str(src), str(tgt))
    _nx_graph = G
    return G

def compute_pagerank(alpha: float = 0.85) -> Dict[str, float]:
    global _pagerank
    if _nx_graph is None:
        build_nx_graph()
    if _nx_graph.number_of_nodes() == 0:
        _pagerank = {}
        return _pagerank
    _pagerank = nx.pagerank(_nx_graph, alpha=alpha)
    return _pagerank

def get_pagerank(doc_path: Path) -> float:
    global _pagerank
    if _pagerank is None:
        compute_pagerank()
    if _pagerank is None:
        return 0.01
    return _pagerank.get(str(doc_path), 0.01)

def get_neighbor_docs(doc_path: Path, direction: str = "both", depth: int = 1, max_neighbors: int = 5) -> List[Path]:
    """获取文档的邻居"""
    visited = set()
    result = []
    queue = [(doc_path, 0)]
    visited.add(doc_path)
    while queue and len(result) < max_neighbors:
        node, d = queue.pop(0)
        if d >= depth:
            continue
        neighbors = set()
        if direction in ("outgoing", "both"):
            neighbors.update(_graph.get(node, set()))
        if direction in ("incoming", "both"):
            neighbors.update(_reverse_graph.get(node, set()))
        for nb in neighbors:
            if nb not in visited:
                visited.add(nb)
                result.append(nb)
                queue.append((nb, d+1))
    return result

def find_path(start: Path, end: Path, max_length: int = 5) -> List[Path]:
    """寻找最短路径"""
    if start == end:
        return [start]
    queue = [(start, [start])]
    visited = {start}
    while queue:
        node, path = queue.pop(0)
        if len(path) > max_length:
            continue
        for neighbor in _graph.get(node, set()):
            if neighbor == end:
                return path + [neighbor]
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append((neighbor, path + [neighbor]))
    return []

def expand_subgraph(seed_paths: List[Path], depth: int = 1, max_nodes: int = 10) -> List[Path]:
    """扩展子图"""
    result = list(seed_paths)
    visited = set(seed_paths)
    queue = [(p, 0) for p in seed_paths]
    while queue and len(result) < max_nodes:
        node, d = queue.pop(0)
        if d >= depth:
            continue
        for nb in _graph.get(node, set()):
            if nb not in visited:
                visited.add(nb)
                result.append(nb)
                queue.append((nb, d+1))
        for nb in _reverse_graph.get(node, set()):
            if nb not in visited:
                visited.add(nb)
                result.append(nb)
                queue.append((nb, d+1))
    return result[:max_nodes]

def retrieve_by_tag(tag: str, top_k: int = 5) -> List[Dict]:
    """通过标签检索文档"""
    results = []
    for doc in _doc_cache.values():
        if tag in doc.get('tags', []):
            results.append(doc)
            if len(results) >= top_k:
                break
    return results