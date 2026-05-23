"""
文档分块器
将 Markdown 文档按标题、段落、长度分割成语义块。
"""
import re
from typing import List, Dict
from config import CHUNK_SIZE, CHUNK_OVERLAP, MIN_CHUNK_SIZE
import frontmatter
from pathlib import Path

def split_by_headings(content: str) -> List[str]:
    """按 Markdown 标题（#）分割，保留标题"""
    # 匹配 # 到下一个 # 或结尾
    sections = re.split(r'\n(?=#{1,6}\s)', content)
    return [s.strip() for s in sections if s.strip()]

def split_by_paragraphs(text: str) -> List[str]:
    """按空行分割段落"""
    paras = re.split(r'\n\s*\n', text)
    return [p.strip() for p in paras if p.strip()]

def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    """将长文本按字符数切块，带重叠"""
    if len(text) <= chunk_size:
        return [text]
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        # 尽量在句子边界断开
        if end < len(text):
            # 找到最后一个句号、问号、感叹号或换行
            last_punct = max(text.rfind('.', start, end), text.rfind('?', start, end), text.rfind('!', start, end), text.rfind('\n', start, end))
            if last_punct > start + chunk_size // 2:
                end = last_punct + 1
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start = end - overlap if end < len(text) else end
    return chunks

def chunk_markdown(file_path: str) -> List[Dict]:
    """
    读取 Markdown 文件，分块并返回块列表
    每个块包含：content, metadata (title, source_path, chunk_index)
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        post = frontmatter.load(f)
    content = post.content
    metadata = post.metadata
    title = metadata.get('title', Path(file_path).stem)

    # 先按标题分割
    sections = split_by_headings(content)
    all_chunks = []
    for sec in sections:
        # 如果单节太长，再按段落切块
        if len(sec) > CHUNK_SIZE:
            paras = split_by_paragraphs(sec)
            for para in paras:
                if len(para) > CHUNK_SIZE:
                    sub_chunks = chunk_text(para)
                    all_chunks.extend(sub_chunks)
                elif len(para) >= MIN_CHUNK_SIZE:
                    all_chunks.append(para)
        else:
            if len(sec) >= MIN_CHUNK_SIZE:
                all_chunks.append(sec)

    # 附加文档级别的元数据到每个块
    result = []
    for idx, chunk in enumerate(all_chunks):
        result.append({
            'content': chunk,
            'metadata': {
                'title': title,
                'source': str(file_path),
                'chunk_index': idx,
                'category': metadata.get('tags', [])[0] if metadata.get('tags') else 'general',
            }
        })
    return result