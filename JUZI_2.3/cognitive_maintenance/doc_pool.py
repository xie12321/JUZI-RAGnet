# doc_pool.py
import numpy as np
from pathlib import Path
from typing import List, Dict, Tuple
from langchain_ollama import OllamaEmbeddings
from logger_config import logger

def build_summary_index(doc_pool: Dict[Path, Dict], embed_model: str) -> Tuple[List[Path], np.ndarray]:
    """
    为文档池中的 summary 字段构建向量索引。
    返回 (doc_paths, embedding_matrix)
    """
    doc_paths = list(doc_pool.keys())
    summaries = [doc_pool[p].get("summary", "") for p in doc_paths]

    embedder = OllamaEmbeddings(model=embed_model)
    logger.info(f"使用嵌入模型 {embed_model} 为 {len(summaries)} 条摘要生成向量...")
    embeddings = embedder.embed_documents(summaries)
    return doc_paths, np.array(embeddings)

def get_similar_docs(current_path: Path, doc_pool: Dict[Path, Dict],
                     doc_paths: List[Path], embedding_matrix: np.ndarray,
                     top_k: int = 3, threshold: float = 0.3) -> List[Path]:
    """
    返回与当前文档摘要最相似的 top_k 个文档路径，排除自身，且相似度需超过 threshold。
    """
    if current_path not in doc_paths:
        return []
    current_idx = doc_paths.index(current_path)
    current_vec = embedding_matrix[current_idx].reshape(1, -1)
    sims = np.dot(current_vec, embedding_matrix.T).flatten()  # 假设向量已归一化
    sims[current_idx] = -1  # 排除自身
    top_indices = np.argsort(sims)[-top_k:][::-1]
    return [doc_paths[i] for i in top_indices if sims[i] > threshold]