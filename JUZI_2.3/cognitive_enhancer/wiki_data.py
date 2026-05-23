# wiki_data.py
from pathlib import Path
from typing import Dict, Set
from collections import defaultdict

from config import get_wiki_root

# 全局数据结构
_doc_cache: Dict[Path, Dict] = {}
_graph: Dict[Path, Set[Path]] = defaultdict(set)
_reverse_graph: Dict[Path, Set[Path]] = defaultdict(set)