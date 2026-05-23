# run.py
import uvicorn
from config import SERVER_PORT
uvicorn.run("server:app", host="0.0.0.0", port=SERVER_PORT, reload=False)