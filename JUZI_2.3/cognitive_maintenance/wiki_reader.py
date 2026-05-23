import frontmatter
import re
from pathlib import Path
from typing import List, Dict
from config import get_wiki_root

def get_all_md_files(root: Path = None) -> List[Path]:
    if root is None:
        root = get_wiki_root()
    return list(root.rglob("*.md"))

def extract_wiki_links(content: str) -> List[str]:
    pattern = r'\[\[([^\]|#]+)(?:#[^\]]*)?(?:\|[^\]]+)?\]\]'
    return [m.strip() for m in re.findall(pattern, content)]

def load_doc_info(path: Path) -> Dict:
    with open(path, 'r', encoding='utf-8') as f:
        post = frontmatter.load(f)
    return {
        "path": path,
        "title": post.metadata.get("title", path.stem),
        "summary": post.metadata.get("summary", ""),
        "content": post.content,
        "tags": post.metadata.get("tags", []),
        "links": extract_wiki_links(post.content),
    }