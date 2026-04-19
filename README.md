# 🌱🍊 JUZI-RAGnet(demo)

> **让语言模型从“种子”成长为“巨子”**  
> *Cognitive Enhancement Layer for Language Models*

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.4.0+-green.svg)](https://github.com/langchain-ai/langgraph)

---

## 📌 什么是 JUZI-RAGnet？

**JUZI-RAGnet** 是一个即插即用的**认知增强层**，它位于“语言模型”与“应用程序”之间，通过工程化的**自省循环**、**分层记忆系统**和**按需检索**，显著提升语言模型在复杂任务中的表现。它可以作为独立服务，以 OpenAI 兼容 API 的形式供任何客户端（如openclaw）调用。

**核心理念**：用架构复杂度换取模型规模 —— 让小语言模型（如 4B 参数量）在特定任务上接近甚至超越传统llm的效果，同时保持**低成本、高隐私、本地部署**。

> **“JUZI”取自中文“巨”与“子”的组合：“巨”代表巨大，“子”是小的后缀（如粒子、种子）。寓意每一个小模型（种子）都能通过这套系统成长为领域“巨子”。**  
> **“RAGnet”则强调检索增强（RAG）与自省循环（网络）的深度融合。**

---

## ✨ 核心特性

| 特性 | 说明 |
|------|------|
| **🔄 自省循环** | 规划 → 工具准备 → 规划验证 → 经验检索 → 工具执行 → 结果验证 → 错误检查 → 输出。模拟人类“先想后审”的思考过程。 |
| **🧠 LLM-Wiki记忆** | 记忆库（用户画像）、经验库（成功/失败案例）、推理库（逻辑学思想）。 |
| **🛠️ 工具调用** | 支持 OpenAI 兼容的外部工具扩展，可接入任何支持的Agent产品 |
| **🎯 结构化输出** | 强制输出 Pydantic 模型，配合规划验证器确保计划合法性。 |
| **🌐 OpenAI 兼容 API** | 无缝接入 OpenClaw、Chatbox 等任何支持该标准的客户端。（还未测试） |
| **🧹 智能记忆整理** | LLM 驱动的自动整理：能够编译，沉淀知识和对话记忆。 |
| **📖 学习能力** | 通过在对话中不断丰富的经验库和记忆库，让LLM越来越聪明。 |

---

## 🧠 架构图

```mermaid
graph TD
    A[用户输入] --> B[推理思考节点]
    B --> C[经验连接节点]
    C --> D[反思检查节点]
    D -->|否| B
    D -->|是| E[最终输出节点]
    F[推理库] --> B
    G[经验库] --> C
    H[记忆库] --> C
    G --> D
    H -->D
 ```

## 🗂️ 记忆整理系统

```mermaid
graph LR
    A[本轮对话] -->|退出/超时| B[记忆整理]
    B -->|LLM 整理| C[推理库]
    B -->|LLM 整理| D[经验库]
    B -->|LLM 整理| E[记忆库]
```

## 🚀 快速开始

### 1. 安装依赖

```bash
git clone https://github.com/yourusername/JUZI-RAGnet.git
cd JUZI-RAGnet
pip install -r requirements.txt
```

### 2. 配置环境（可选，用于联网搜索）

```bash
echo "TAVILY_API_KEY=your_tavily_api_key" > .env
```

### 3. 启动 Ollama

```bash
ollama pull fredrezones55/qwen3.5-opus:4b
ollama pull shaw/dmeta-embedding-zh-small-q4:latest
ollama serve
```

### 4. 运行

```bash
# 命令行交互
python main.py

# 启动 API 服务(未测试）
python api.py
```

### 5. 调用 API（OpenAI 兼容）

```bash
import openai
client = openai.OpenAI(base_url="http://localhost:8000/v1", api_key="dummy")
response = client.chat.completions.create(
    model="enhancer",
    messages=[{"role": "user", "content": "北京今天天气怎么样？"}]
)
print(response.choices[0].message.content)
```
---

## ⚙️ 配置说明

编辑 `config.py` 可调整关键参数：

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `LLM_MODEL` | 使用的语言模型 | `qwen3.5:4b` |
| `EMBED_MODEL` | 嵌入模型（可选） | `qwen3-embedding:0.6b` |
| `MAX_ITERATIONS` | 自省循环最大迭代次数 | `3` |
| `MID_TERM_MAX_MESSAGES` | 记忆最大条数 | `10` |

---

## 🧩 扩展开发

### 添加新知识

在 `wiki/` 下的不同文件夹下建立新的.md文件

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！请确保：

- 代码符合 PEP8 风格
- 新功能包含必要的注释和文档
- 提交前运行 `python -m pytest` 确保测试通过

详见 [CONTRIBUTING.md](CONTRIBUTING.md)。

---

## 📄 许可证

本项目采用 **Apache 2.0 许可证**，详情见 [LICENSE](LICENSE) 文件。

---

## 🙏 致谢

- [LangChain](https://github.com/langchain-ai/langchain) – 基础组件
- [LangGraph](https://github.com/langchain-ai/langgraph) – 图编排
- [Ollama](https://ollama.com/) – 本地模型运行
- [Chroma](https://www.trychroma.com/) – 向量数据库
- [Tavily](https://tavily.com/) – 搜索 API

---

### 如果这个项目对你有帮助，请给一个 ⭐️ Star 支持一下！
让更多语言模型从种子成长为“巨子”。

