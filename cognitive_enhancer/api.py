from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from controller import run_self_reflection
from wiki_reader import build_index
from logger_config import logger

app = FastAPI(title="Cognitive Enhancer API")

# 允许跨域（可根据需要限制来源）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Request(BaseModel):
    user_input: str
    external_info: Optional[str] = None
    history: Optional[List[Dict[str, str]]] = []

class Response(BaseModel):
    result: str
    error: Optional[str] = None

@app.on_event("startup")
async def startup():
    build_index()
    logger.info("Cognitive Enhancer API started")

@app.post("/v1/cognitive/reflect", response_model=Response)
async def reflect(req: Request):
    try:
        result = run_self_reflection(
            user_input=req.user_input,
            external_info=req.external_info,
            history=req.history
        )
        return Response(result=result)
    except Exception as e:
        logger.error(f"Reflection failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))