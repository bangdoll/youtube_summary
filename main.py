import os
import sys
import json
import asyncio
import logging
import secrets
import base64
import io
import time
import pydantic
from typing import List
from PIL import Image
from concurrent.futures import ThreadPoolExecutor
from fastapi import FastAPI, Request, Response, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import HTMLResponse, StreamingResponse, RedirectResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from authlib.integrations.starlette_client import OAuth
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

# Import our core engine
import youtube_summary
import slide_generator

# Import Cost Tracker
try:
    from cost_tracker import tracker as cost_tracker
except ImportError:
    # Handle case where it might be run from a different context
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from cost_tracker import tracker as cost_tracker

app = FastAPI(title="PrismFlow")

# Trust Proxy Headers (CRITICAL for Cloud Run/Render behind Load Balancer)
# This ensures request.url is seen as HTTPS, preventing redirect_uri mismatches and session cookie issues
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts=["*"])

# Session middleware for OAuth
# Use a stable key if env var not set, to prevent session invalidation on restart
# In production, users SHOULD set SECRET_KEY env var
DEFAULT_SECRET_KEY = "stable_secret_key_for_youtube_summary_app_fix_restart_auth_issue"
SECRET_KEY = os.getenv("SECRET_KEY", DEFAULT_SECRET_KEY) 
app.add_middleware(
    SessionMiddleware, 
    secret_key=SECRET_KEY, 
    max_age=1209600, # 14 Days (14 * 24 * 60 * 60)
    https_only=True, # Secure only
    same_site="lax"
)

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

# Use /tmp for Cloud Run compatibility (in-memory filesystem)
TEMP_DIR = "/tmp/youtube_summary_temp"
os.makedirs(TEMP_DIR, exist_ok=True)

# Mount static files
# Note: Mount specific path /static/temp FIRST to take precedence
app.mount("/static/temp", StaticFiles(directory=TEMP_DIR), name="static_temp")
app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")

# Lock for single-threaded execution
processing_lock = asyncio.Lock()

# [v7.0] Session storage for slide images (避免前端重傳圖片導致 413)
# 格式: {session_id: {"images": [PIL.Image], "timestamp": float}}
slide_sessions = {}


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
    redirect_uri = str(request.url_for("auth_callback"))
    
    # Force HTTPS in production (non-localhost)
    # This fixes the 'redirect_uri_mismatch' 400 error on Cloud Run/Render
    if "localhost" not in redirect_uri and "127.0.0.1" not in redirect_uri:
        redirect_uri = redirect_uri.replace("http://", "https://")
    
    print(f"[Auth] Redirect URI sent to Google: {redirect_uri}") # Debug log
    
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
async def summarize(request: Request, url: str, gemini_key: str = None, openai_key: str = None):
    """SSE Endpoint that streams processing logs and final result."""
    # Check authentication
    # Logic:
    # 1. If User provides Key -> Allow (BYOK Mode)
    # 2. If User Logged In & Authorized -> Allow (Server Key Mode)
    # 3. Else -> Deny
    
    is_authorized = False
    
    # Check for BYOK
    if gemini_key or openai_key:
        is_authorized = True
    
    # Check for Login (if not already authorized via BYOK)
    if not is_authorized and is_auth_enabled():
        user_email = get_user_email(request)
        if user_email and is_allowed_user(user_email):
            is_authorized = True
            
    if not is_authorized:
        async def error_gen():
            yield f"data: {json.dumps({'type': 'error', 'message': '❌ 請先登入或在設定中填入您的 API Key'})}\\n\\n"
        return StreamingResponse(error_gen(), media_type="text/event-stream")
    
    return StreamingResponse(event_generator(url, gemini_key, openai_key), media_type="text/event-stream")



async def event_generator(url: str, gemini_key: str = None, openai_key: str = None):
    yield f"data: {json.dumps({'type': 'log', 'data': '🔌 連線建立中...'})}\n\n"
    
    if processing_lock.locked():
        yield f"data: {json.dumps({'type': 'error', 'message': '⚠️ 系統正忙於處理另一個影片，請稍候。'})}\n\n"
        return

    async with processing_lock:
        queue = asyncio.Queue()
        yield f"data: {json.dumps({'type': 'log', 'data': '🚀 系統核心已啟動'})}\n\n"
        
        # Log Auth Status for debugging
        auth_status = "✅ 已啟用 (Google OAuth)" if is_auth_enabled() else "⚠️ 未啟用 (使用 Local 模式)"
        yield f"data: {json.dumps({'type': 'log', 'data': f'🔒 安全模組: {auth_status}'})}\n\n"
        if is_auth_enabled():
             yield f"data: {json.dumps({'type': 'log', 'data': f'👤 允許清單: {len(ALLOWED_EMAILS)} 位使用者'})}\n\n"

        loop = asyncio.get_running_loop()
        
        # Check cost limit warning
        try:
            current_cost = cost_tracker.get_total_cost()
            if cost_tracker.is_limit_exceeded(limit=20.0):
                yield f"data: {json.dumps({'type': 'log', 'data': f'⚠️ 注意：本月 API 使用量預估已達 ${current_cost:.2f} USD (超過 $20 限額)'})}\n\n"
            else:
                 yield f"data: {json.dumps({'type': 'log', 'data': f'📊 本月 API 累計使用量: ${current_cost:.4f} USD'})}\n\n"
        except Exception as e:
            logging.error(f"Cost tracker check failed: {e}")
            yield f"data: {json.dumps({'type': 'log', 'data': f'⚠️ 無法取得成本資訊: {str(e)}'})}\n\n"

        def log_callback(msg, *args, **kwargs):
            formatted_msg = str(msg)
            loop.call_soon_threadsafe(queue.put_nowait, formatted_msg)

        youtube_summary.set_log_callback(log_callback)
        
        executor = ThreadPoolExecutor(max_workers=1)
        future = loop.run_in_executor(executor, run_processing_safe, url, gemini_key, openai_key)
        
        start_time = asyncio.get_running_loop().time()
        
        while True:
            try:
                while not queue.empty():
                    msg = queue.get_nowait()
                    yield f"data: {json.dumps({'type': 'log', 'data': msg})}\n\n"
                
                # Check for completion
                if future.done():
                    try:
                        filename, content = future.result()
                        clean_filename = os.path.basename(filename)
                        yield f"data: {json.dumps({'type': 'result', 'data': content, 'filename': clean_filename})}\n\n"
                        yield f"data: {json.dumps({'type': 'done'})}\n\n"
                    except Exception as e:
                        yield f"data: {json.dumps({'type': 'error', 'message': f'❌ 發生錯誤: {str(e)}'})}\n\n"
                    break
                
                # Enforce global timeout (10 mins = 600s)
                if asyncio.get_running_loop().time() - start_time > 600:
                     yield f"data: {json.dumps({'type': 'error', 'message': '❌ 處理逾時 (10分鐘)，系統強制終止。'})}\n\n"
                     # We cannot kill the thread easily, but we break the loop to release the lock (via async with processing_lock exit)
                     break
                
                try:
                    msg = await asyncio.wait_for(queue.get(), timeout=2.0)
                    yield f"data: {json.dumps({'type': 'log', 'data': msg})}\n\n"
                except asyncio.TimeoutError:
                    # Send a ping
                    yield f"data: {json.dumps({'type': 'ping'})}\n\n"
                    continue
                    
            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'message': f'系統錯誤: {str(e)}'})}\n\n"
                break
        
        youtube_summary.set_log_callback(print)


def run_processing_safe(url, gemini_key=None, openai_key=None):
    """Wrapper to run the pipeline."""
    return youtube_summary.process_video_pipeline(url, gemini_key=gemini_key, openai_key=openai_key)

@app.post("/api/preview-pdf")
async def preview_pdf(file: UploadFile = File(...)):
    """
    接收 PDF，回傳所有頁面的預覽圖片 URL。
    """
    if not file.filename.lower().endswith(".pdf"):
        return JSONResponse(status_code=400, content={"error": "請上傳 PDF 檔案"})

    try:
        pdf_bytes = await file.read()
        
        # 使用線程池執行轉檔，避免阻塞 Event Loop
        loop = asyncio.get_running_loop()
        image_urls = await loop.run_in_executor(
            None, 
            slide_generator.generate_preview_images, 
            pdf_bytes, 
            TEMP_DIR
        )
        
        return JSONResponse({
            "total_pages": len(image_urls),
            "images": image_urls
        })
        
    except Exception as e:
        print(f"Preview PDF Error: {e}")
        return JSONResponse(status_code=500, content={"error": f"預覽生成失敗: {str(e)}"})

    except Exception as e:
        print(f"Preview PDF Error: {e}")
        return JSONResponse(status_code=500, content={"error": f"預覽生成失敗: {str(e)}"})


@app.post("/api/analyze-slides")
async def analyze_slides(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    gemini_key: str = Form(None),  # 改為選填，允許使用伺服器端金鑰
    selected_pages: str = Form(None),
    remove_icon: bool = Form(False)
):
    # 如果前端沒傳 gemini_key，使用環境變數
    effective_gemini_key = gemini_key or os.getenv("GOOGLE_API_KEY", "")
    """
    [Web Editor Step 1] 接收 PDF，進行分析與去字，但不生成 PPTX。
    回傳: Streaming NDJSON
    {"progress": 1, "total": 10}
    {"analyses": [...], "cleaned_images": [...]}
    """
    if not file.filename.lower().endswith(".pdf"):
        return JSONResponse(status_code=400, content={"error": "請上傳 PDF 檔案"})

    # Read file content first
    # Remove redundant read that consumes the stream
    # pdf_bytes = await file.read() was causing the file pointer to be at the end


    # Queue for streaming events
    queue = asyncio.Queue()

    # Save Uploaded File to Temp
    temp_pdf_filename = f"upload_{secrets.token_hex(8)}.pdf"
    temp_pdf_path = os.path.join(TEMP_DIR, temp_pdf_filename)
    
    try:
        with open(temp_pdf_path, "wb") as f:
            while content := await file.read(1024 * 1024):  # 1MB chunks
                f.write(content)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"儲存暫存檔案失敗: {e}"})

    async def run_analysis():
        try:
            # Helper for logging to frontend
            async def log(msg):
                print(f"[{file.filename}] {msg}")
                await queue.put({"type": "log", "data": msg})

            await log("正在初始化分析引擎...")

            # 解析 selected_pages
            selected_indices = None
            if selected_pages:
                try:
                    selected_indices = json.loads(selected_pages)
                    if not isinstance(selected_indices, list):
                        selected_indices = None
                    else:
                        await log(f"使用者指定分析頁面: {selected_indices}")
                except:
                    pass
            
            async def report_progress(current, total, message=None):
                data = {"progress": current, "total": total}
                if message:
                    data["message"] = message
                    # Also emit log for message
                    # await queue.put({"type": "log", "data": message}) # Fixed: Duplicated in frontend
                await queue.put(data)

            # Send initial feedback
            await log("正在讀取 PDF 結構與初始化分析...")

            # 1. 執行核心分析
            await log(f"正在呼叫 Gemini Vision Model ({slide_generator.ANALYSIS_MODEL_ID}) 進行視覺分析...")
            analyses, cleaned_images = await slide_generator.analyze_presentation(
                temp_pdf_path, effective_gemini_key, file.filename, selected_indices, 
                remove_icon=remove_icon,
                progress_callback=report_progress
            )
            # 2. 轉為 Base64 (Stateless)
            await log(f"視覺分析完成，共產出 {len(cleaned_images)} 張圖片，正在轉碼傳輸...")
            cleaned_image_urls = []
            loop = asyncio.get_running_loop()
            
            for i, img in enumerate(cleaned_images):
                try:
                    # [v6.1 Fix] Robust Fallback for Reconstruction Mode
                    if img is None:
                        # Create a standard white slide placeholder (16:9)
                        img = Image.new('RGB', (1600, 900), (255, 255, 255))

                    # Handle Transparency (RGBA/P) -> RGB with White Background
                    if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
                        background = Image.new('RGB', img.size, (255, 255, 255))
                        if img.mode == 'P':
                            img = img.convert('RGBA')
                        background.paste(img, mask=img.split()[-1])
                        img = background
                    elif img.mode != 'RGB':
                        img = img.convert('RGB')
                        
                    # Convert to Base64
                    def image_to_base64(pil_img):
                        # Resize if too large (Max 1280px) to reduce payload
                        pil_img.thumbnail((1280, 1280)) 
                        
                        buffered = io.BytesIO()
                        # Optimize JPEG size (Quality 70 is good balance)
                        pil_img.save(buffered, format="JPEG", quality=70, optimize=True)
                        return base64.b64encode(buffered.getvalue()).decode('utf-8')

                    b64_str = await loop.run_in_executor(None, image_to_base64, img)
                    cleaned_image_urls.append(f"data:image/jpeg;base64,{b64_str}")
                    
                except Exception as img_err:
                    print(f"Image {i} encode failed: {img_err}")
                    # Error Placeholder (Red X)
                    cleaned_image_urls.append("data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAxMDAgMTAwIj48cmVjdCB3aWR0aD0iMTAwIiBoZWlnaHQ9IjEwMCIgZmlsbD0iI2ZmZWFZWEiIC8+PHBhdGggZD0iTTEwIDEwTDkwIDkwTTEwIDkwTDkwIDEwIiBzdHJva2U9InJlZCIgc3Ryb2tlLXdpZHRoPSI1IiAvPjwvc3ZnPg==")
            
            await log("圖片處理完成，正在回傳結果...")

            # [v7.0] 建立 Session 儲存圖片 (避免前端重傳)
            session_id = secrets.token_hex(16)
            slide_sessions[session_id] = {
                "images": cleaned_images,  # PIL Images
                "timestamp": time.time()
            }
            print(f"[Session] Created session: {session_id} with {len(cleaned_images)} images")

            # 清理過期 session (30 分鐘)
            cleanup_old_sessions()

            # Result
            await queue.put({
                "analyses": analyses,
                "cleaned_images": cleaned_image_urls,
                "session_id": session_id  # 新增
            })
            
        except Exception as e:
            import traceback
            error_msg = f"分析流程嚴重錯誤: {str(e)}\n{traceback.format_exc()}"
            print(error_msg)
            await queue.put({"error": str(e)}) # Send concise error to UI
        finally:
            print(f"[{file.filename}] Task finished. Cleaning up.")
            await queue.put(None) # Signal end
            # Cleanup PDF
            try:
                if os.path.exists(temp_pdf_path):
                    os.remove(temp_pdf_path)
            except:
                pass

    # Start background task
    asyncio.create_task(run_analysis())

    async def event_generator():
        while True:
            data = await queue.get()
            if data is None:
                break
            # NDJSON format
            yield json.dumps(data) + "\n"

    return StreamingResponse(event_generator(), media_type="application/x-ndjson")


class GenerateSlidesRequest(pydantic.BaseModel):
    analyses: List[dict]
    session_id: str = None  # [v7.0] 新增：從 session 取圖片
    cleaned_images: List[str] = []  # 向後兼容，但優先用 session_id
    filename: str = "presentation"


def cleanup_old_sessions():
    """清理超過 30 分鐘的 session"""
    now = time.time()
    expired = [k for k, v in slide_sessions.items() if now - v["timestamp"] > 1800]
    for k in expired:
        del slide_sessions[k]
        print(f"[Session] Expired: {k}")

@app.post("/api/generate-slides-data")
async def generate_slides_data(
    request: Request,
    data: GenerateSlidesRequest
):
    """
    [Web Editor Step 2] 接收前端編輯後的 JSON 資料與圖片路徑，生成 PPTX。
    """
    try:
        pil_images = []

        # [v7.0] 優先使用 session_id 取圖片
        if data.session_id and data.session_id in slide_sessions:
            session = slide_sessions[data.session_id]
            pil_images = session["images"]
            print(f"[Generate Slides] Using session: {data.session_id}, {len(pil_images)} images")
            
            # 確保轉為 RGB
            for i, img in enumerate(pil_images):
                if img is None:
                    pil_images[i] = Image.new('RGB', (1600, 900), (255, 255, 255))
                elif img.mode != 'RGB':
                    pil_images[i] = img.convert('RGB')
        
        # 向後兼容：如果沒有 session_id 但有 cleaned_images
        elif data.cleaned_images:
            print(f"[Generate Slides] Fallback: Using Base64 images ({len(data.cleaned_images)} images)")
            for img_str in data.cleaned_images:
                try:
                    if img_str.startswith("data:image"):
                        # Parse Base64: data:image/jpeg;base64,.....
                        header, encoded = img_str.split(",", 1)
                        img_bytes = base64.b64decode(encoded)
                        img = Image.open(io.BytesIO(img_bytes))
                        # FORCE RGB: PPTX/JPEG saving fails with RGBA/P modes
                        if img.mode != 'RGB':
                            img = img.convert('RGB')
                        pil_images.append(img)
                    else:
                        # Legacy or Error Placeholder
                        if img_str.startswith("/static/temp/"):
                            filename = os.path.basename(img_str)
                            file_path = os.path.join(TEMP_DIR, filename)
                            if os.path.exists(file_path):
                                img = Image.open(file_path)
                                if img.mode != 'RGB': img = img.convert('RGB')
                                pil_images.append(img)
                            else:
                                pil_images.append(Image.new('RGB', (1024, 768), 'white'))
                        else:
                            pil_images.append(Image.new('RGB', (1024, 768), 'white'))
                except Exception as e:
                    print(f"Image decode failed: {e}")
                    pil_images.append(Image.new('RGB', (1024, 768), 'white'))
        
        # 如果都沒有圖片，報錯
        if not pil_images:
            return JSONResponse(status_code=400, content={"error": "Session 已過期或無圖片資料，請重新分析"})

        # 2. 生成 PPTX
        output_dir = os.path.join(TEMP_DIR, "slides")
        os.makedirs(output_dir, exist_ok=True)
        
        output_filename = f"{os.path.splitext(data.filename)[0]}_edited.pptx"
        output_path = os.path.join(output_dir, output_filename)
        
        await asyncio.to_thread(
            slide_generator.create_pptx_from_analysis, 
            data.analyses, 
            pil_images, 
            output_path
        )
        
        return FileResponse(
            output_path,
            media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            filename=output_filename
        )

    except Exception as e:
        print(f"Generate Slides Data Error: {e}")
        return JSONResponse(status_code=500, content={"error": f"生成失敗: {str(e)}"})


@app.post("/api/generate-slides")
async def generate_slides(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    gemini_key: str = Form(None),
    selected_pages: str = Form(None)
):
    """
    [Legacy] 接收 PDF 檔案，使用 Gemini Vision 分析並生成 PPTX。
    保留給舊版 UI 使用。
    """
    # 驗證輸入
    if not gemini_key:
        return JSONResponse(
            status_code=400, 
            content={"error": "請提供 Gemini API Key (BYOK 模式)"}
        )
    
    if not file.filename.lower().endswith(".pdf"):
        return JSONResponse(
            status_code=400,
            content={"error": "請上傳 PDF 檔案"}
        )

    try:
        # 讀取 PDF 內容
        pdf_bytes = await file.read()
        
        # 解析 selected_pages
        selected_indices = None
        if selected_pages:
            try:
                selected_indices = json.loads(selected_pages)
                if not isinstance(selected_indices, list):
                    selected_indices = None
            except Exception as e:
                print(f"解析 selected_pages 失敗: {e}")
                
        # 進行處理
        pptx_path = await slide_generator.process_pdf_to_slides(
            pdf_bytes=pdf_bytes,
            api_key=gemini_key,
            filename=file.filename,
            selected_indices=selected_indices
        )
        
        # 設定回傳檔名
        output_filename = os.path.splitext(file.filename)[0] + ".pptx"
        output_filename = output_filename.encode('utf-8').decode('latin-1') # 避免 header 亂碼

        # 設定背景任務刪除暫存擋
        # 注意: FileResponse 完成後通常不會自動刪除，需自行管理或使用 tempfile
        # 這裡簡單實作：延遲刪除 (不完美但可用)
        
        return FileResponse(
            pptx_path,
            media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            filename=output_filename
        )

    except ValueError as ve:
        return JSONResponse(status_code=400, content={"error": str(ve)})
    except Exception as e:
        print(f"Slide Gen Error: {e}")
        return JSONResponse(status_code=500, content={"error": f"生成失敗: {str(e)}"})


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
