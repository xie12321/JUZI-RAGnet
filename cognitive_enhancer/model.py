from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from config import LLM_MODEL, LLM_BASE_URL, LLM_API_KEY

if "ollama" in LLM_BASE_URL or "localhost" in LLM_BASE_URL:
    llm = ChatOllama(model=LLM_MODEL, base_url=LLM_BASE_URL, temperature=0.7, reasoning=False)
else:
    llm = ChatOpenAI(model=LLM_MODEL, base_url=LLM_BASE_URL, api_key=LLM_API_KEY, temperature=0.7)