import os
import asyncio
import time
from fastapi import FastAPI

app = FastAPI()

@app.get("/test")
async def test_endpoint():
    pid = os.getpid()
    # Simulate a 1-second database task
    await asyncio.sleep(0.003) 
    print(f"Worker {pid} finished a request.")
    return {"worker_pid": pid}