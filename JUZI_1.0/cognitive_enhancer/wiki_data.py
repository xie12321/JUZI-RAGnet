# wiki_data.py
from pathlib import Path
from typing import Dict, Set
from collections import defaultdict

# 注意：WIKI_ROOT 从 config 导入，避免循环
from config import WIKI_ROOT

# 全局数据结构
_doc_cache: Dict[Path, Dict] = {}
_graph: Dict[Path, Set[Path]] = defaultdict(set)
_reverse_graph: Dict[Path, Set[Path]] = defaultdict(set)