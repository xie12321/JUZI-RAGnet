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
USE_EMBEDDING = os.getenv("USE_EMBEDDING", "false").lower() == "false"
EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")

# 循环控制
MAX_ITERATIONS = 3

# API 配置
API_HOST = "0.0.0.0"
API_PORT = 8000

# 确保目录存在
for sub in [REASONING_DIR, EXPERIENCE_DIR, MEMORY_DIR, "ChatHistory"]:
    (WIKI_ROOT / sub).mkdir(parents=True, exist_ok=True)
