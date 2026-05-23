# server.py
import json
import asyncio
from concurrent.futures import ThreadPoolExecutor
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from logger_config import logger
import main as maintenance
import config as cfg

app = FastAPI()
executor = ThreadPoolExecutor(max_workers=1)


@app.websocket("/ws/maintenance")
async def websocket_maintenance(websocket: WebSocket):
    await websocket.accept()
    logger.info("维护系统 WebSocket 连接建立")
    task_running = False
    loop = asyncio.get_event_loop()

    def progress_callback(stage, current, total, message):
        payload = {
            "stage": stage,
            "current": current,
            "total": total,
            "message": message
        }
        if current == 0 and total == 0:
            payload["type"] = "stage_complete"
        else:
            payload["type"] = "progress"
        asyncio.run_coroutine_threadsafe(
            websocket.send_text(json.dumps(payload)),
            loop
        )

    try:
        while True:
            data = await websocket.receive_text()
            req = json.loads(data)
            action = req.get("action")
            payload = req.get("payload", {})

            wiki_root = payload.get("wiki_root")
            if wiki_root:
                cfg.set_wiki_root(wiki_root)
                logger.info(f"Wiki root updated to: {wiki_root}")

            if action == "run_health_check":
                if task_running:
                    await websocket.send_text(json.dumps({"type": "error", "message": "已有任务运行中"}))
                    continue
                task_running = True
                mode = payload.get("mode", "incremental")
                execution_mode = payload.get("execution_mode", "direct")
                model_config = payload.get("model_config", {})
                embed_model = payload.get("embed_model", "nomic-embed-text")
                try:
                    orphans = await loop.run_in_executor(
                        executor,
                        maintenance.run_health_check,
                        mode, execution_mode, model_config, embed_model, progress_callback
                    )
                    await websocket.send_text(json.dumps({"type": "done", "orphans": [str(p) for p in orphans]}))
                except Exception as e:
                    await websocket.send_text(json.dumps({"type": "error", "message": str(e)}))
                finally:
                    task_running = False

            elif action == "run_import":
                if task_running:
                    await websocket.send_text(json.dumps({"type": "error", "message": "已有任务运行中"}))
                    continue
                text = payload.get("import_text", "")
                if not text:
                    await websocket.send_text(json.dumps({"type": "error", "message": "缺少导入文本"}))
                    continue
                execution_mode = payload.get("execution_mode", "direct")
                model_config = payload.get("model_config", {})
                task_running = True
                try:
                    result = await loop.run_in_executor(
                        executor,
                        maintenance.run_import_task,
                        text, model_config, execution_mode, None
                    )
                    await websocket.send_text(json.dumps({"type": "done", "result": result}))
                except Exception as e:
                    await websocket.send_text(json.dumps({"type": "error", "message": str(e)}))
                finally:
                    task_running = False

            elif action == "precipitate_pools":
                if task_running:
                    await websocket.send_text(json.dumps({"type": "error", "message": "已有任务运行中"}))
                    continue
                task_running = True
                try:
                    await loop.run_in_executor(
                        executor,
                        maintenance.run_pool_precipitation,
                        progress_callback
                    )
                    await websocket.send_text(json.dumps({"type": "done", "message": "暂存区沉淀完成"}))
                except Exception as e:
                    await websocket.send_text(json.dumps({"type": "error", "message": str(e)}))
                finally:
                    task_running = False

            elif action == "cancel":
                await websocket.send_text(json.dumps({"type": "error", "message": "取消功能暂未实现"}))
            else:
                await websocket.send_text(json.dumps({"type": "error", "message": f"未知 action: {action}"}))
    except WebSocketDisconnect:
        logger.info("维护系统 WebSocket 断开")