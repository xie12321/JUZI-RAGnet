import os
import json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# 内部可变全局路径
_wiki_root = None

def _init_wiki_root():
    global _wiki_root
    # 1. 环境变量优先
    env_root = os.getenv("WIKI_ROOT")
    if env_root:
        _wiki_root = Path(env_root)
        return
    # 2. 读取 Electron 配置文件
    config_path = Path.home() / ".cognitive_enhancer_config.json"
    try:
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            wiki_root = data.get("wikiRoot")
            if wiki_root:
                _wiki_root = Path(wiki_root)
                return
    except Exception:
        pass
    # 3. 默认值
    _wiki_root = Path("./wiki")

def get_wiki_root() -> Path:
    """获取当前知识库根目录（首次调用自动初始化）"""
    global _wiki_root
    if _wiki_root is None:
        _init_wiki_root()
    return _wiki_root

def set_wiki_root(path: str):
    """动态设置知识库根目录，并自动创建必要子目录"""
    global _wiki_root
    _wiki_root = Path(path)
    for sub in [REASONING_DIR, EXPERIENCE_DIR, MEMORY_DIR, "ChatHistory"]:
        (_wiki_root / sub).mkdir(parents=True, exist_ok=True)

# LLM 配置
LLM_MODEL = os.getenv("LLM_MODEL", "qwen3.5:4b")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://localhost:11434")
LLM_API_KEY = os.getenv("LLM_API_KEY", "ollama")

# 知识库子目录
REASONING_DIR = "Reasoning"
EXPERIENCE_DIR = "Experience"
MEMORY_DIR = "Memory"

# 嵌入模型配置
USE_EMBEDDING = os.getenv("USE_EMBEDDING", "false").lower() in ("true", "1", "yes")
EMBED_MODEL = os.getenv("EMBED_MODEL", "qwen3-embedding:0.6B")

# 循环控制
MAX_ITERATIONS = 3

# API 配置
API_HOST = "0.0.0.0"
API_PORT = 8000

# 分块配置
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
MIN_CHUNK_SIZE = 100

# 混合检索配置
BM25_WEIGHT = 0.3
VECTOR_WEIGHT = 0.7
HYBRID_TOP_K = 10

# 向量数据库（Chroma）配置
CHROMA_PATH = Path("./chroma_db")
CHROMA_COLLECTION_NAME = "wiki_chunks"

# 全局模型配置（GUI 同步）
CURRENT_MODEL_CONFIG = {
    "type": "ollama",
    "model": "qwen3.5:4b",
    "api_base": "http://localhost:11434/v1",
    "api_key": "ollama",
    "temperature": 0.7
}

# 全局嵌入模型配置（GUI 同步）
CURRENT_EMBED_MODEL = "nomic-embed-text"