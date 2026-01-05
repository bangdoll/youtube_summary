import os
import sys
import json
import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

# Import our core engine
import youtube_summary

app = FastAPI(title="Youtube Summary AI")

# Ensure web directory exists (handled by creation steps, but good for safety)
WEB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")
os.makedirs(WEB_DIR, exist_ok=True)

# Mount static files
app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")

# Lock for single-threaded execution to prevent global state collision
processing_lock = asyncio.Lock()

@app.get("/")
async def read_root():
    index_path = os.path.join(WEB_DIR, "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>Web Interface Loading...</h1><p>Please ensure web/index.html exists.</p>")

@app.get("/api/summarize")
async def summarize(url: str):
    """
    SSE Endpoint that streams processing logs and final result.
    """
    return StreamingResponse(event_generator(url), media_type="text/event-stream")

async def event_generator(url: str):
    # Check lock to prevent concurrent usage (simplified for this tool)
    if processing_lock.locked():
        yield f"data: {json.dumps({'type': 'error', 'message': '⚠️ 系統正忙於處理另一個影片，請稍候。'})}\n\n"
        return

    async with processing_lock:
        queue = asyncio.Queue()
        loop = asyncio.get_running_loop()
        
        def log_callback(msg, *args, **kwargs):
            # This runs in the worker thread, so we must schedule the queue put on the main loop
            formatted_msg = str(msg)
            loop.call_soon_threadsafe(queue.put_nowait, formatted_msg)

        # Set the global callback on the module
        # This is safe ONLY because we have the processing_lock
        youtube_summary.set_log_callback(log_callback)
        
        # Run the blocking function in a separate thread
        executor = ThreadPoolExecutor(max_workers=1)
        future = loop.run_in_executor(executor, run_processing_safe, url)
        
        # Loop to consume queue and check future status
        while True:
            try:
                # checking queue and future
                # We intentionally poll rapidly or wait for queue
                
                # First, drain any pending logs
                while not queue.empty():
                    msg = queue.get_nowait()
                    yield f"data: {json.dumps({'type': 'log', 'data': msg})}\n\n"
                
                # Check if done
                if future.done():
                    try:
                        filename, content = future.result()
                        # Send success result
                        yield f"data: {json.dumps({'type': 'result', 'data': content, 'filename': filename})}\n\n"
                        yield f"data: {json.dumps({'type': 'done'})}\n\n"
                    except Exception as e:
                        # Send error
                        yield f"data: {json.dumps({'type': 'error', 'message': f'❌ 發生錯誤: {str(e)}'})}\n\n"
                    break
                
                # Wait a bit for more logs or completion
                # We use wait_for on the queue to sleep efficiently
                try:
                    msg = await asyncio.wait_for(queue.get(), timeout=0.5)
                    yield f"data: {json.dumps({'type': 'log', 'data': msg})}\n\n"
                except asyncio.TimeoutError:
                    continue
                    
            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'message': f'系統錯誤: {str(e)}'})}\n\n"
                break
        
        # Reset callback to print just in case
        youtube_summary.set_log_callback(print)

def run_processing_safe(url):
    """Wrapper to run the pipeline."""
    return youtube_summary.process_video_pipeline(url)

if __name__ == "__main__":
    import uvicorn
    # Run server
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
