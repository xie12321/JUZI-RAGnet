import frontmatter
from pathlib import Path
from typing import List, Optional

from wiki_reader import load_doc_info


def write_doc(path: Path, content: str, title: Optional[str] = None,
              summary: Optional[str] = None, tags: Optional[List[str]] = None):
    path.parent.mkdir(parents=True, exist_ok=True)
    post = frontmatter.loads(content)
    if title:
        post.metadata["title"] = title
    if summary:
        post.metadata["summary"] = summary
    if tags:
        post.metadata["tags"] = tags
    with open(path, 'w', encoding='utf-8') as f:
        f.write(frontmatter.dumps(post))

def update_metadata(path: Path, title: Optional[str] = None,
                   summary: Optional[str] = None, tags: Optional[List[str]] = None):
    with open(path, 'r', encoding='utf-8') as f:
        post = frontmatter.load(f)
    if title is not None:
        post.metadata["title"] = title
    if summary is not None:
        post.metadata["summary"] = summary
    if tags is not None:
        post.metadata["tags"] = tags
    with open(path, 'w', encoding='utf-8') as f:
        f.write(frontmatter.dumps(post))

def append_links(path: Path, link_titles: List[str]):
    existing = load_doc_info(path)["links"]
    new_links = [f"[[{title}]]" for title in link_titles if title not in existing]
    if not new_links:
        return
    with open(path, 'a', encoding='utf-8') as f:
        f.write("\n\n## 相关内容\n")
        for link in new_links:
            f.write(f"- {link}\n")