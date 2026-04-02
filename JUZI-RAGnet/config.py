# config.py
import os
from pathlib import Path

# 模型配置
LLM_MODEL = "fredrezones55/qwen3.5-opus:4b"
EMBED_MODEL = "shaw/dmeta-embedding-zh-small-q4:latest"

# 路径配置
BASE_DIR = Path(__file__).parent
REASONING_DIR = BASE_DIR / "reasoning_kb"
MEMORY_DIR = BASE_DIR / "faiss_memory_index"
EXPERIENCE_DIR = BASE_DIR / "experience_kb"
MID_TERM_FILE = BASE_DIR / "mid_term_memory.json"
SKILLS_DIR = BASE_DIR / "skills" / "builtin"

# 循环控制
MAX_ITERATIONS = 3

# 中期记忆配置
MID_TERM_MAX_MESSAGES = 30
IMPORTANCE_KEYWORDS = ["记住", "重要", "不要忘记", "我的名字", "我叫", "我叫"]

# 确保目录存在
os.makedirs(REASONING_DIR, exist_ok=True)
os.makedirs(MEMORY_DIR, exist_ok=True)
os.makedirs(EXPERIENCE_DIR, exist_ok=True)