import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# LLM 配置
LLM_MODEL = os.getenv("LLM_MODEL", "qwen3.5:4b")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://localhost:11434")
LLM_API_KEY = os.getenv("LLM_API_KEY", "ollama")

# Wiki 根目录
WIKI_ROOT = Path("./wiki")

# 知识库子目录（必须与 wiki_reader.py 中一致）
REASONING_DIR = "Reasoning"     # 推理库：思维框架、逻辑方法
EXPERIENCE_DIR = "Experience"   # 经验库：公式、算法、规律、教训
MEMORY_DIR = "Memory"           # 记忆库：用户画像、历史事实

# 嵌入模型配置（可选，若不需要可设为 False）
USE_EMBEDDING = os.getenv("USE_EMBEDDING", "false").lower() in ("true", "1", "yes")# WikiRetriever 类的初始化逻辑并没有根据 USE_EMBEDDING 配置来决定是否使用向量检索，而是直接初始化了 OllamaEmbeddings 并尝试构建/加载 Chroma 向量库
EMBED_MODEL = os.getenv("EMBED_MODEL", "qwen3-embedding:0.6B")

# 循环控制
MAX_ITERATIONS = 3

# API 配置
API_HOST = "0.0.0.0"
API_PORT = 8000

# 分块配置
CHUNK_SIZE = 500           # 每个块的最大字符数（近似）
CHUNK_OVERLAP = 50         # 块之间的重叠字符数
MIN_CHUNK_SIZE = 100       # 最小块大小，小于此值不单独成块

# 混合检索配置
BM25_WEIGHT = 0.3          # BM25 得分权重
VECTOR_WEIGHT = 0.7        # 向量检索得分权重
HYBRID_TOP_K = 10          # 混合检索初步返回的块数（之后可再取 top_k）

# 向量数据库（Chroma）配置
CHROMA_PATH = Path("./chroma_db")          # Chroma 持久化目录
CHROMA_COLLECTION_NAME = "wiki_chunks"     # 集合名称（用于存储所有文档块）

# 确保目录存在
for sub in [REASONING_DIR, EXPERIENCE_DIR, MEMORY_DIR, "ChatHistory"]:
    (WIKI_ROOT / sub).mkdir(parents=True, exist_ok=True)