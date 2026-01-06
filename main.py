import os
import sys
import json
import asyncio
import logging
import secrets
from concurrent.futures import ThreadPoolExecutor
from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse, StreamingResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from authlib.integrations.starlette_client import OAuth

# Import our core engine
import youtube_summary

app = FastAPI(title="Youtube Summary AI")

# Session middleware for OAuth
SECRET_KEY = os.getenv("SECRET_KEY", secrets.token_hex(32))
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

# OAuth setup
oauth = OAuth()
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
ALLOWED_EMAILS = os.getenv("ALLOWED_EMAILS", "").split(",")

if GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET:
    oauth.register(
        name="google",
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )

# Ensure web directory exists
WEB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")
os.makedirs(WEB_DIR, exist_ok=True)

# Mount static files
app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")

# Lock for single-threaded execution
processing_lock = asyncio.Lock()


def is_auth_enabled():
    """Check if Google OAuth is configured."""
    return bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET)


def get_user_email(request: Request):
    """Get the logged-in user's email from session."""
    return request.session.get("user_email")


def is_allowed_user(email: str):
    """Check if the email is in the allowed list."""
    if not ALLOWED_EMAILS or ALLOWED_EMAILS == [""]:
        return True  # No restriction if no emails configured
    return email in ALLOWED_EMAILS


@app.get("/")
async def read_root(request: Request):
    index_path = os.path.join(WEB_DIR, "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>Web Interface Loading...</h1>")


@app.get("/api/check-auth")
async def check_auth(request: Request):
    """Check authentication status."""
    if not is_auth_enabled():
        return {"auth_required": False, "logged_in": True}
    
    user_email = get_user_email(request)
    if user_email and is_allowed_user(user_email):
        return {"auth_required": True, "logged_in": True, "email": user_email}
    
    return {"auth_required": True, "logged_in": False}


@app.get("/auth/login")
async def login(request: Request):
    """Redirect to Google OAuth login."""
    if not is_auth_enabled():
        return RedirectResponse(url="/")
    
    # Determine redirect URI
    redirect_uri = request.url_for("auth_callback")
    # Force HTTPS in production
    if "onrender.com" in str(redirect_uri):
        redirect_uri = str(redirect_uri).replace("http://", "https://")
    
    return await oauth.google.authorize_redirect(request, redirect_uri)


@app.get("/auth/callback")
async def auth_callback(request: Request):
    """Handle Google OAuth callback."""
    if not is_auth_enabled():
        return RedirectResponse(url="/")
    
    try:
        token = await oauth.google.authorize_access_token(request)
        user_info = token.get("userinfo")
        
        if not user_info:
            return HTMLResponse("<h1>❌ 無法取得使用者資訊</h1>", status_code=400)
        
        email = user_info.get("email", "")
        
        if not is_allowed_user(email):
            return HTMLResponse(f"<h1>❌ 未授權</h1><p>{email} 不在允許的使用者清單中。</p>", status_code=403)
        
        # Store user info in session
        request.session["user_email"] = email
        request.session["user_name"] = user_info.get("name", "")
        request.session["user_picture"] = user_info.get("picture", "")
        
        return RedirectResponse(url="/")
    
    except Exception as e:
        return HTMLResponse(f"<h1>❌ 登入失敗</h1><p>{str(e)}</p>", status_code=400)


@app.get("/auth/logout")
async def logout(request: Request):
    """Clear session and log out."""
    request.session.clear()
    return RedirectResponse(url="/")


@app.get("/api/user")
async def get_user(request: Request):
    """Get current user info."""
    if not is_auth_enabled():
        return {"email": "local", "name": "Local User", "picture": ""}
    
    return {
        "email": request.session.get("user_email", ""),
        "name": request.session.get("user_name", ""),
        "picture": request.session.get("user_picture", ""),
    }


@app.get("/api/summarize")
async def summarize(request: Request, url: str):
    """SSE Endpoint that streams processing logs and final result."""
    # Check authentication
    if is_auth_enabled():
        user_email = get_user_email(request)
        if not user_email or not is_allowed_user(user_email):
            async def error_gen():
                yield f"data: {json.dumps({'type': 'error', 'message': '❌ 請先登入'})}\\n\\n"
            return StreamingResponse(error_gen(), media_type="text/event-stream")
    
    return StreamingResponse(event_generator(url), media_type="text/event-stream")


async def event_generator(url: str):
    if processing_lock.locked():
        yield f"data: {json.dumps({'type': 'error', 'message': '⚠️ 系統正忙於處理另一個影片，請稍候。'})}\\n\\n"
        return

    async with processing_lock:
        queue = asyncio.Queue()
        loop = asyncio.get_running_loop()
        
        def log_callback(msg, *args, **kwargs):
            formatted_msg = str(msg)
            loop.call_soon_threadsafe(queue.put_nowait, formatted_msg)

        youtube_summary.set_log_callback(log_callback)
        
        executor = ThreadPoolExecutor(max_workers=1)
        future = loop.run_in_executor(executor, run_processing_safe, url)
        
        while True:
            try:
                while not queue.empty():
                    msg = queue.get_nowait()
                    yield f"data: {json.dumps({'type': 'log', 'data': msg})}\\n\\n"
                
                if future.done():
                    try:
                        filename, content = future.result()
                        yield f"data: {json.dumps({'type': 'result', 'data': content, 'filename': filename})}\\n\\n"
                        yield f"data: {json.dumps({'type': 'done'})}\\n\\n"
                    except Exception as e:
                        yield f"data: {json.dumps({'type': 'error', 'message': f'❌ 發生錯誤: {str(e)}'})}\\n\\n"
                    break
                
                try:
                    msg = await asyncio.wait_for(queue.get(), timeout=0.5)
                    yield f"data: {json.dumps({'type': 'log', 'data': msg})}\\n\\n"
                except asyncio.TimeoutError:
                    continue
                    
            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'message': f'系統錯誤: {str(e)}'})}\\n\\n"
                break
        
        youtube_summary.set_log_callback(print)


def run_processing_safe(url):
    """Wrapper to run the pipeline."""
    return youtube_summary.process_video_pipeline(url)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
