import os
import json
from pathlib import Path

# 动态路径内部变量
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

# 其他配置保持不变
REASONING_DIR = "Reasoning"
EXPERIENCE_DIR = "Experience"
MEMORY_DIR = "Memory"

ENHANCER_API_BASE = os.environ.get("ENHANCER_API_BASE", "http://localhost:8000/v1")
ENHANCER_API_KEY = "dummy"
LLM_TEMPERATURE = 0.2

SERVER_PORT = int(os.environ.get("MAINTENANCE_SERVER_PORT", 8001))