# wiki_retriever.py
import os
import json
import numpy as np
from pathlib import Path
from typing import List, Dict, Tuple
import chromadb
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings
from rank_bm25 import BM25Okapi
from config import WIKI_ROOT, CHROMA_PATH, CHROMA_COLLECTION_NAME, EMBED_MODEL, HYBRID_TOP_K, BM25_WEIGHT, VECTOR_WEIGHT
from logger_config import logger
from wiki_chunker import chunk_markdown
from wiki_data import _doc_cache, _graph, _reverse_graph   # 新增导入
from wiki_graph import get_pagerank, get_neighbor_docs, expand_subgraph, find_path, retrieve_by_tag

class WikiRetriever:
    def __init__(self, rebuild: bool = False):
        self.embeddings = OllamaEmbeddings(model=EMBED_MODEL)
        self.client = chromadb.PersistentClient(path=str(CHROMA_PATH))
        self.collection_name = CHROMA_COLLECTION_NAME
        self.vector_store = None
        self.bm25_index = None
        self.chunk_id_to_doc = {}
        self.all_chunks_text = []
        self._init_retriever(rebuild)

    def _init_retriever(self, rebuild: bool):
        if rebuild:
            try:
                self.client.delete_collection(self.collection_name)
            except:
                pass
            self._build_index()
        else:
            try:
                self.vector_store = Chroma(
                    client=self.client,
                    collection_name=self.collection_name,
                    embedding_function=self.embeddings,
                )
                self._load_bm25_index()
                logger.info("Loaded existing retrieval index")
            except Exception as e:
                logger.warning(f"Failed to load existing index: {e}, rebuilding...")
                self._build_index()

    def _build_index(self):
        all_md_files = list(WIKI_ROOT.rglob("*.md"))
        all_chunks = []
        for md_file in all_md_files:
            if '.obsidian' in md_file.parts:
                continue
            chunks = chunk_markdown(str(md_file))
            all_chunks.extend(chunks)

        if not all_chunks:
            logger.warning("No chunks found, empty index")
            return

        texts = []
        metadatas = []
        ids = []
        for idx, chunk in enumerate(all_chunks):
            chunk_id = f"chunk_{idx}"
            texts.append(chunk['content'])
            metadatas.append(chunk['metadata'])
            ids.append(chunk_id)
            self.chunk_id_to_doc[chunk_id] = chunk
            self.all_chunks_text.append(chunk['content'])

        self.vector_store = Chroma.from_texts(
            texts=texts,
            embedding=self.embeddings,
            client=self.client,
            collection_name=self.collection_name,
            metadatas=metadatas,
            ids=ids
        )

        tokenized_corpus = [self._tokenize(text) for text in self.all_chunks_text]
        self.bm25_index = BM25Okapi(tokenized_corpus)
        self._save_bm25_index()
        logger.info(f"Built index with {len(all_chunks)} chunks")

    def _tokenize(self, text: str) -> List[str]:
        import re
        # 简单分词（可替换为 jieba 提高中文效果）
        words = re.findall(r'[\u4e00-\u9fa5]+|[a-zA-Z]+', text)
        return words

    def _save_bm25_index(self):
        if not self.bm25_index:
            return

        # 准备可序列化的 chunk_id_to_doc
        chunk_map_serializable = {}
        for chunk_id, doc in self.chunk_id_to_doc.items():
            # 复制 metadata 并将 Path 对象转为字符串
            metadata = doc['metadata'].copy()
            if 'source' in metadata and isinstance(metadata['source'], Path):
                metadata['source'] = str(metadata['source'])
            chunk_map_serializable[chunk_id] = {
                'content': doc['content'],
                'metadata': metadata
            }
        data = {
            'corpus': self.all_chunks_text,
            'doc_freqs': self.bm25_index.doc_freqs,
            'idf': self.bm25_index.idf,
            'avgdl': self.bm25_index.avgdl,
            'corpus_len': len(self.all_chunks_text),
            'chunk_id_to_doc': chunk_map_serializable
        }
        save_path = CHROMA_PATH / 'bm25_index.json'
        save_path.parent.mkdir(parents=True, exist_ok=True)
        with open(save_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False)

    def _load_bm25_index(self):
        load_path = CHROMA_PATH / 'bm25_index.json'
        if not load_path.exists():
            raise FileNotFoundError("BM25 index not found")
        with open(load_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        self.all_chunks_text = data['corpus']
        # 恢复 chunk_id_to_doc
        self.chunk_id_to_doc = {
            chunk_id: {
                'content': doc['content'],
                'metadata': doc['metadata']
            }
            for chunk_id, doc in data.get('chunk_id_to_doc', {}).items()
        }
        tokenized_corpus = [self._tokenize(text) for text in self.all_chunks_text]
        self.bm25_index = BM25Okapi(tokenized_corpus)

    def vector_search(self, query: str, k: int = 10) -> List[Tuple[int, float, str]]:
        if not self.vector_store:
            return []
        results = self.vector_store.similarity_search_with_score(query, k=k)
        chunk_indices = []
        chunk_keys = list(self.chunk_id_to_doc.keys())
        for doc, score in results:
            chunk_id = doc.metadata.get('id')
            if not chunk_id:
                for cid, chunk in self.chunk_id_to_doc.items():
                    if chunk['content'] == doc.page_content:
                        chunk_id = cid
                        break
            if chunk_id and chunk_id in self.chunk_id_to_doc:
                try:
                    idx = chunk_keys.index(chunk_id)
                    similarity = 1 - score
                    chunk_indices.append((idx, similarity, chunk_id))
                except ValueError:
                    pass
        return chunk_indices

    def bm25_search(self, query: str, k: int = 10) -> List[Tuple[int, float]]:
        if not self.bm25_index:
            return []
        tokenized_query = self._tokenize(query)
        scores = self.bm25_index.get_scores(tokenized_query)
        # 确保 scores 长度与 chunk_id_to_doc 一致
        expected_len = len(self.chunk_id_to_doc)
        if len(scores) != expected_len:
            logger.warning(f"BM25 scores length {len(scores)} != expected {expected_len}, truncating/padding")
            if len(scores) > expected_len:
                scores = scores[:expected_len]
            else:
                # 补零（理论上不应发生）
                scores = list(scores) + [0.0] * (expected_len - len(scores))
        # 获取 top k 索引
        top_indices = np.argsort(scores)[::-1][:k]
        # 过滤掉可能仍超出范围的索引（双重保险）
        valid_indices = [(idx, scores[idx]) for idx in top_indices if idx < len(self.chunk_id_to_doc)]
        return valid_indices

    def hybrid_search(self, query: str, top_k: int = HYBRID_TOP_K) -> List[Dict]:
        vector_results = self.vector_search(query, k=top_k * 2)
        bm25_results = self.bm25_search(query, k=top_k * 2)
        rank_dict = {}

        chunk_keys = list(self.chunk_id_to_doc.keys())
        max_idx = len(chunk_keys) - 1

        for rank, (idx, score, chunk_id) in enumerate(vector_results):
            if idx < 0 or idx > max_idx:
                logger.warning(f"Invalid vector index {idx}, skipping")
                continue
            rrf_score = 1 / (60 + rank + 1)
            rank_dict[idx] = rank_dict.get(idx, 0) + rrf_score * VECTOR_WEIGHT

        for rank, (idx, score) in enumerate(bm25_results):
            if idx < 0 or idx > max_idx:
                logger.warning(f"Invalid BM25 index {idx}, skipping")
                continue
            rrf_score = 1 / (60 + rank + 1)
            rank_dict[idx] = rank_dict.get(idx, 0) + rrf_score * BM25_WEIGHT

        sorted_indices = sorted(rank_dict.keys(), key=lambda x: rank_dict[x], reverse=True)[:top_k]

        results = []
        for idx in sorted_indices:
            if idx > max_idx:
                continue
            chunk_id = chunk_keys[idx]
            chunk = self.chunk_id_to_doc[chunk_id]
            results.append({
                'content': chunk['content'],
                'metadata': chunk['metadata'],
                'score': rank_dict[idx]
            })
        return results

    def hybrid_search_with_graph(self, query: str, categories: List[str] = None, top_k: int = 10,
                                 expand_neighbors: bool = True) -> List[Dict]:
        """
        混合检索 + 知识图谱增强，支持按类别过滤
        categories: 需要检索的知识库类别列表，如 ["experience", "memory"]，None 表示所有
        """

        # 辅助函数：从路径判断类别
        def _get_category_from_path(path_str: str) -> str:
            if 'Reasoning' in path_str or 'reasoning' in path_str:
                return 'reasoning'
            elif 'Experience' in path_str or 'experience' in path_str:
                return 'experience'
            elif 'Memory' in path_str or 'memory' in path_str:
                return 'memory'
            else:
                return 'other'

        # 1. 基础混合检索
        candidates = self.hybrid_search(query, top_k=top_k * 2)

        # 2. 按类别过滤（如果指定了 categories）
        if categories:
            filtered = []
            for cand in candidates:
                src_path = cand['metadata'].get('source', '')
                cat = _get_category_from_path(src_path)
                if cat in categories:
                    filtered.append(cand)
            candidates = filtered[:top_k * 2]

        # 3. PageRank 重排序
        for cand in candidates:
            src_path = cand['metadata'].get('source')
            if src_path:
                pr = get_pagerank(Path(src_path))
                cand['score'] *= (1 + 0.3 * pr)

        # 4. 子图扩展（不限制类别）
        expanded = []
        if expand_neighbors:
            for cand in candidates[:top_k]:
                expanded.append(cand)
                src_path = cand['metadata'].get('source')
                if src_path:
                    neighbors = get_neighbor_docs(Path(src_path), depth=1, max_neighbors=2)
                    for nb_path in neighbors:
                        nb_doc = _doc_cache.get(nb_path)
                        if nb_doc:
                            expanded.append({
                                'content': nb_doc.get('summary', ''),
                                'metadata': {'source': str(nb_path), 'title': nb_doc.get('title', '')},
                                'score': cand['score'] * 0.8
                            })
        else:
            expanded = candidates

        # 5. 标签聚合（不限制类别）
        import re
        tag_match = re.search(r'#(\w+)', query)
        if tag_match:
            tag = tag_match.group(1)
            tag_docs = retrieve_by_tag(tag, top_k=3)
            for doc in tag_docs:
                expanded.append({
                    'content': doc.get('summary', ''),
                    'metadata': {'source': str(doc['path']), 'title': doc.get('title', '')},
                    'score': 0.5
                })

        # 6. 按分数排序并返回 top_k
        expanded.sort(key=lambda x: x['score'], reverse=True)
        logger.info(f"Hybrid search with graph returned {len(expanded)} results for query: {query[:50]}...")
        return expanded[:top_k]

# 全局单例
_retriever = None
def get_retriever(rebuild: bool = False) -> WikiRetriever:
    global _retriever
    if _retriever is None or rebuild:
        _retriever = WikiRetriever(rebuild=rebuild)
    return _retriever