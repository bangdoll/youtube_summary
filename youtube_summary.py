#!/usr/bin/env python3
import os
import sys
import argparse
import re
from datetime import datetime
from dotenv import load_dotenv
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter
import openai
import yt_dlp

# Load environment variables
load_dotenv()

# Import Cost Tracker
try:
    from cost_tracker import tracker as cost_tracker
except ImportError:
    # Handle case where it might be run from a different context
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from cost_tracker import tracker as cost_tracker

# Global logger callback (default to print)
LOG_FUNC = print

def set_log_callback(func):
    """Sets the global logging function."""
    global LOG_FUNC
    LOG_FUNC = func

def log(msg, *args, **kwargs):
    """Wrapper for global logger."""
    if LOG_FUNC:
        LOG_FUNC(msg, *args, **kwargs)

def get_video_id(url):
    """Extracts video ID from Youtube URL."""
    # Examples:
    # https://www.youtube.com/watch?v=VIDEO_ID
    # https://youtu.be/VIDEO_ID
    video_id = None
    if "youtube.com" in url:
        try:
            video_id = url.split("v=")[1].split("&")[0]
        except:
            video_id = None
    elif "youtu.be" in url:
        try:
            video_id = url.split("/")[-1].split("?")[0]
        except:
            video_id = None
            
    if not video_id:
        log("錯誤：無法從網址中提取影片 ID。")
        raise Exception("錯誤：無法從網址中提取影片 ID。")
    return video_id

def get_transcript(video_id):
    """Fetches transcript using youtube_transcript_api CLI via subprocess."""
    import subprocess
    import json
    
    # Path to the executable
    # Check if we are checking local mac path or linux
    cli_path = "youtube_transcript_api"
    # On Render/Docker, it should be in PATH. 
    # If not, we can try invoking module directly via python -m but the subprocess call below expects an executable.
    
    cmd = [
        cli_path,
        video_id,
        "--languages", "zh-Hant", "zh-TW", "zh-Hans", "zh-CN", "en",
        "--format", "text"
    ]
    
    log(f"執行 CLI 指令: {' '.join(cmd)}")
    
    try:
        # Run the command and capture output
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        # Check if stdout contains error message strings (CLI sometimes prints errors to stdout)
        if "Could not retrieve a transcript" in result.stdout:
            log("Transcript CLI 回傳錯誤訊息。")
            return None
            
        return result.stdout
    except subprocess.CalledProcessError as e:
        log(f"Transcript CLI 警告: {e}")
        # Return None to trigger fallback
        return None
    except FileNotFoundError:
        # Fallback if full path doesn't exist, try just the command name
        try:
            cmd[0] = "youtube_transcript_api"
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return result.stdout
        except Exception as e:
            log(f"Transcript CLI Warning: {e}")
            return None

def analyze_transcript(transcript, video_title="Unknown Video", video_url=""):
    """Sends transcript to LLM for analysis."""
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        error_msg = "錯誤：在環境變數或 .env 檔案中找不到 OPENAI_API_KEY。\n請在您的 .env 檔案中設定：OPENAI_API_KEY=sk-..."
        log(error_msg)
        raise Exception(error_msg)
        
    client = openai.OpenAI(api_key=api_key)
    
    # Read the prompt template
    prompt_path = os.path.join(os.path.dirname(__file__), "prompts", "video_summary.md")
    try:
        with open(prompt_path, "r", encoding="utf-8") as f:
            system_prompt_template = f.read()
    except FileNotFoundError:
        error_msg = f"錯誤：找不到提示詞檔案於 {prompt_path}"
        log(error_msg)
        raise Exception(error_msg)
        
    # Fill dynamic variables in prompt
    current_date = datetime.now().strftime("%Y-%m-%d")
    system_prompt = system_prompt_template.replace("{{current_date}}", current_date)
    system_prompt = system_prompt.replace("{{video_title}}", video_title)
    system_prompt = system_prompt.replace("{{video_url}}", video_url)

    log("正在傳送請求至 OpenAI...")
    try:
        response = client.chat.completions.create(
            model="gpt-4o", # Or gpt-4-turbo
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": transcript}
            ],
            temperature=0.7
        )
        
        # Track cost
        if response.usage:
            cost = cost_tracker.track_chat(
                response.model, 
                response.usage.prompt_tokens, 
                response.usage.completion_tokens
            )
            log(f"本次分析預估成本: ${cost:.4f}")

        return response.choices[0].message.content
    except Exception as e:
        log(f"呼叫 OpenAI API 時發生錯誤: {e}")
        raise Exception(f"呼叫 OpenAI API 時發生錯誤: {e}")


def analyze_with_gemini(youtube_url, video_title="Unknown"):
    """
    Analyzes a YouTube video directly using Gemini.
    No need to download or transcribe - Gemini can watch the video!
    """
    from google import genai
    from google.genai import types
    
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        error_msg = "錯誤：找不到 GOOGLE_API_KEY 環境變數。"
        log(error_msg)
        raise Exception(error_msg)
    
    # Initialize client (New google-genai SDK)
    client = genai.Client(api_key=api_key)
    
    # Read prompt template
    prompt_path = os.path.join(os.path.dirname(__file__), "prompts", "video_summary.md")
    try:
        with open(prompt_path, "r", encoding="utf-8") as f:
            prompt_template = f.read()
    except FileNotFoundError:
        prompt_template = "請分析這個影片並提供詳細的摘要。"
    
    # Fill dynamic variables
    current_date = datetime.now().strftime("%Y-%m-%d")
    prompt = prompt_template.replace("{{current_date}}", current_date)
    prompt = prompt.replace("{{video_title}}", video_title)
    prompt = prompt.replace("{{video_url}}", youtube_url)
    prompt += "\n\n請直接觀看這個影片並按照上述格式生成筆記。"
    
    log("正在使用 Gemini 3 Flash Preview (最新預覽版)...")
    log(f"影片 URL: {youtube_url}")
    
    try:
        # Use Gemini 3 Flash Preview
        # Verified available in user's account and list_models_v2.py output
        response = client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=[
                types.Part.from_uri(file_uri=youtube_url, mime_type="video/*"),
                prompt
            ]
        )
        
        log("Gemini 分析完成！")
        return response.text

        
    except Exception as e:
        error_str = str(e)
        # Check for "Too many images" or "Invalid Argument" which implies video is too long for direct processing
        if "400" in error_str and ("images" in error_str or "INVALID_ARGUMENT" in error_str):
            log("⚠️ 影片過長 (超過 3 小時或幀數限制)，切換至 Audio Upload 模式...")
            return analyze_long_video_fallback(client, youtube_url, prompt_template, video_title)
            
        log(f"Gemini 分析失敗: {e}")
        # If it's another error, we let it fall back to Transcript method
        raise e

def analyze_long_video_fallback(client, youtube_url, prompt_template, video_title):
    """
    Fallback for long videos: Download audio -> Upload to Gemini -> Analyze Audio File.
    This bypasses the video frame limit.
    """
    from google import genai
    from google.genai import types
    import time
    
    # 1. Download Audio
    log("正在下載音訊檔案 (Long Video Fallback)...")
    # Reuse existing audio download logic, but we need the filename
    # We can use get_audio_and_transcribe's logic but just get the file
    audio_file = download_audio_file(youtube_url)
    if not audio_file:
         raise Exception("無法下載音訊檔案進行備援分析")
         
    # 2. Upload to Gemini
    log(f"正在上傳音訊至 Gemini ({os.path.basename(audio_file)})...")
    try:
        # Upload using the new SDK (Files API)
        # Note: The new SDK might handle uploads via client.files.upload
        # But 'client' here is the genai.Client
        
        # Let's verify the exact upload syntax for google-genai v2
        # Usually: client.files.upload(path=...) returns a File object
        file_obj = client.files.upload(path=audio_file)
        log(f"上傳成功. File URI: {file_obj.uri}")
        
        # 3. Wait for processing
        log("等待 Gemini 處理音訊檔案...")
        while file_obj.state.name == "PROCESSING":
            time.sleep(2)
            file_obj = client.files.get(name=file_obj.name)
            
        if file_obj.state.name != "ACTIVE":
             raise Exception(f"File processing failed. State: {file_obj.state.name}")
             
        # 4. Generate Content
        # Fill prompt similar to before, but modify instruction for Audio
        current_date = datetime.now().strftime("%Y-%m-%d")
        prompt = prompt_template.replace("{{current_date}}", current_date)
        prompt = prompt.replace("{{video_title}}", video_title)
        prompt = prompt.replace("{{video_url}}", youtube_url)
        prompt += "\n\n(注意：這是影片的純音訊軌。請根據音訊內容進行分析)"
        
        log("開始分析長音訊...")
        response = client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=[
                types.Part.from_uri(file_uri=file_obj.uri, mime_type=file_obj.mime_type),
                prompt
            ]
        )
        log("長影片分析完成！")
        
        # Cleanup local file
        try:
            os.remove(audio_file)
        except:
            pass
            
        return response.text
        
    except Exception as e:
        log(f"Audio Fallback 失敗: {e}")
        raise e

def download_audio_file(url):
    """Helper to just download audio and return path."""
    import yt_dlp
    import time
    
    # Use same PO Token opts
    opts = get_yt_dlp_opts()
    # Force filename to be temp path
    output_filename = f"temp_long_audio_{int(time.time())}" # yt-dlp will add extension
    opts['outtmpl'] = output_filename
    opts['format'] = 'bestaudio/best'
    opts['postprocessors'] = [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '128', # Lower quality is fine for speech, saves bandwidth
    }]
    
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])
        # yt-dlp might append .mp3
        if os.path.exists(output_filename + ".mp3"):
            return output_filename + ".mp3"
        # Check for other possible extensions if mp3 failed
        for ext in ['m4a', 'webm', 'ogg', 'flac', 'aac']:
            if os.path.exists(output_filename + "." + ext):
                return output_filename + "." + ext
        return None
    except Exception as e:
        log(f"yt-dlp download failed: {e}")
        # Try Playwright fallback? 
        # For now, return None and let caller handle
        return None

def save_note(content, video_id):
    """Saves the content to a markdown file."""
    # Extract title from content if possible (first line usually)
    lines = content.strip().split('\n')
    title = f"Video_{video_id}"
    for line in lines:
        if line.startswith("# "):
            title = line[2:].strip()
            # Sanitize filename
            title = re.sub(r'[\\/*?:"<>|]', "", title)
            break
            
    # Save to parent Notes directory to keep Obsidian folder structure clean
    # Assuming script is now in a subfolder "youtube_summary"
    base_dir = os.path.dirname(os.path.abspath(__file__))
    notes_dir = os.path.join(base_dir, "..", "Notes")
    
    # Ensure directory exists
    os.makedirs(notes_dir, exist_ok=True)
    
    filename = os.path.join(notes_dir, f"{title}.md")
    
    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)
        
    log(f"成功！筆記已完成， {os.path.basename(filename)}")
    return filename



# Global cookie file path
COOKIE_FILE = "cookies.txt"

def setup_cookies():
    """Writes cookies from env var to file for yt-dlp/playwright."""
    cookie_content = os.getenv("YOUTUBE_COOKIES")
    if cookie_content:
        # Check if content needs formatting (e.g. if passed as JSON or raw string)
        # For now assume Netscape format string
        with open(COOKIE_FILE, "w") as f:
            f.write(cookie_content)
        return True
    return os.path.exists(COOKIE_FILE)

def get_yt_dlp_opts():
    import yt_dlp
    import tempfile

    proxy_url = os.getenv("PROXY_URL")
    
    opts = {
        # Accept any audio format, fall back to best video if no audio
        'format': 'ba*/b',  
        'quiet': True,
        'no_warnings': True,
        'noplaylist': True,
        # Mimic a real browser
        'user_agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'nocheckcertificate': True,
        # 'ignoreerrors': True,  # REMOVED: We want to catch errors to trigger Playwright fallback
    }

    # Add cookies if available
    if setup_cookies():
         log("🍪 使用 Cookies 進行驗證")
         opts['cookiefile'] = COOKIE_FILE
    
    # Add proxy if configured
    if proxy_url:
        if "example.com" not in proxy_url:
            log(f"使用代理伺服器: {proxy_url.split('@')[-1] if '@' in proxy_url else proxy_url}")
            opts['proxy'] = proxy_url
        else:
            log("⚠️ 偵測到範例代理設定 (example.com)，已自動忽略。")

    # === [PO Token Integration] ===
    # Attempt to generate PO Token to bypass "Sign in to confirm you're not a bot"
    if generate_po_token_nodes:
        try:
            log("正在生成 PO Token 以繞過 Bot 偵測...")
            # This generates the parameters needed for extractor_args
            token_data = generate_po_token_nodes()
            po_token = token_data.get('po_token')
            visitor_data = token_data.get('visitor_data')
            
            if po_token and visitor_data:
                log(f"PO Token 生成成功.")
                # Inject into yt-dlp extractor_args
                # Syntax: 'youtube':{'po_token':['...'], 'visitor_data':['...']}
                opts['extractor_args'] = {
                    'youtube': {
                        'po_token': [po_token],
                        'visitor_data': [visitor_data]
                    }
                }
        except Exception as e:
            log(f"PO Token 生成失敗 (非致命錯誤): {e}")

    return opts






def get_video_info(url):
    """Extracts video info using yt-dlp."""
    try:
        opts = get_yt_dlp_opts()
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return info
    except Exception as e:
        log(f"Error extracting video info: {e}")
        raise e

    
def process_video_pipeline(url):
    """Orchestrates the video processing pipeline. Returns (filename, note_content)."""
    # Ensure cookies are set up (env var -> file)
    setup_cookies()
    
    video_id = get_video_id(url)
    log(f"處理影片 ID: {video_id}")
    
    # Construct canonical URL
    canonical_url = f"https://www.youtube.com/watch?v={video_id}"
    
    # Get Title (optional, Gemini can get it too)
    video_title = "未知的影片"
    try:
        info = get_video_info(canonical_url)
        video_title = info.get('title', f"Video_{video_id}")
        log(f"影片標題: {video_title}")
    except Exception as e:
        video_title = f"Video_{video_id}"
        log(f"警告：無法取得影片標題 ({e})。繼續執行。")
    
    # === METHOD 1: Try Gemini Direct Analysis (Best - no download needed!) ===
    google_api_key = os.getenv("GOOGLE_API_KEY")
    if google_api_key:
        try:
            log("嘗試使用 Gemini 直接分析影片...")
            analysis = analyze_with_gemini(canonical_url, video_title)
            filename = save_note(analysis, video_id)
            return filename, analysis
        except Exception as e:
            log(f"Gemini 分析失敗: {e}")
            log("改用傳統逐字稿方法...")
    else:
        log("未設定 GOOGLE_API_KEY，跳過 Gemini 分析...")
    
    # === METHOD 2: Fallback to Transcript-based Analysis ===
    log("正在取得逐字稿...")
    transcript = get_transcript(video_id)
    
    if not transcript:
        transcript = get_audio_and_transcribe(url)
        
    if not transcript:
        log("嚴重錯誤：無法透過任何方式取得逐字稿。")
        raise Exception("嚴重錯誤：無法透過任何方式取得逐字稿。")
    
    log("正在分析內容...")
    analysis = analyze_transcript(transcript, video_title, url)
    
    filename = save_note(analysis, video_id)
    return filename, analysis

def main():
    parser = argparse.ArgumentParser(description="AI Agent: Convert Youtube Video to Structured Note")
    parser.add_argument("url", help="Youtube Video URL")
    args = parser.parse_args()
    
    try:
        process_video_pipeline(args.url)
    except Exception as e:
        log(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

def download_audio_playwright(url):
    """
    Uses Playwright to bypass YouTube bot detection and capture audio stream URL.
    Falls back from yt-dlp when traditional methods fail.
    """
    import requests
    from playwright.sync_api import sync_playwright
    
    log("[Playwright] 啟動無頭瀏覽器...")
    
    audio_urls = []
    output_file = "temp_audio_playwright.webm"
    
    def intercept_request(request):
        """Capture audio stream URLs from network requests."""
        req_url = request.url
        # Debug: Log all googlevideo requests to analyze patterns
        if 'googlevideo.com' in req_url:
            log(f"[Network] Request: {req_url[:60]}...")
            
        # YouTube audio streams contain these patterns
        if 'googlevideo.com' in req_url and ('audio' in req_url or 'mime=audio' in req_url):
            audio_urls.append(req_url)
            log(f"[Playwright] 捕獲到音訊 URL")
    
    try:
        with sync_playwright() as p:
            # Check for proxy
            proxy_url = os.getenv("PROXY_URL")
            launch_opts = {
                'headless': True,
                'ignore_default_args': ["--mute-audio"] # CRITICAL: Ensure audio is not muted in headless
            }
            
            if proxy_url and "example.com" not in proxy_url:
                log(f"[Playwright] 使用代理: {proxy_url.split('@')[-1] if '@' in proxy_url else proxy_url}")
                launch_opts['proxy'] = {'server': proxy_url}
            elif proxy_url:
                log("[Playwright] ⚠️ 偵測到範例代理設定 (example.com)，已自動忽略。")
            
            # Launch headless Chromium
            browser = p.chromium.launch(**launch_opts)
            # Helper to parse Netscape cookies for Playwright
            def parse_netscape_cookies(path):
                cookies = []
                try:
                    with open(path, 'r') as f:
                        for line in f:
                            if line.startswith('#') or not line.strip(): continue
                            parts = line.split('\t')
                            if len(parts) >= 7:
                                cookies.append({
                                    'name': parts[5],
                                    'value': parts[6].strip(),
                                    'domain': parts[0],
                                    'path': parts[2],
                                    'expires': int(parts[4]) if parts[4] else -1,
                                    'httpOnly': parts[3] == 'TRUE',
                                    'secure': parts[3] == 'TRUE' # Approximation
                                })
                except Exception as e:
                     log(f"[Playwright] Cookie parsing failed: {e}")
                return cookies

            # Desktop User Agent (stealth mode)
            user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
            
            # Use the browser instance launched above
            
            # Emulate Desktop with Stealth Headers
            context = browser.new_context(
                user_agent=user_agent,
                viewport={'width': 1920, 'height': 1080},
                device_scale_factor=1,
                is_mobile=False,
                has_touch=False,
                locale='en-US',
                extra_http_headers={
                    'Referer': 'https://www.youtube.com/',
                    'Origin': 'https://www.youtube.com',
                    'Accept-Language': 'en-US,en;q=0.9'
                }
            )
            
            # Parse Netscape cookies and inject
            if os.path.exists(COOKIE_FILE):
                try:
                     cookies = parse_netscape_cookies(COOKIE_FILE)
                     # Filter cookies for domain (playwright strictness)
                     # Fix: Ensure domain starts with .youtube.com or youtube.com
                     valid_cookies = []
                     for c in cookies:
                         c['sameSite'] = 'None'
                         c['secure'] = True
                         if 'youtube' in c['domain']:
                             valid_cookies.append(c)
                             
                     if valid_cookies:
                        context.add_cookies(valid_cookies)
                        log(f"[Playwright] 🍪 已載入 {len(valid_cookies)} 個 Cookies (Desktop Context)")
                except Exception as e:
                    log(f"[Playwright] Cookie 載入失敗: {e}")

            page = context.new_page()
            # Use on('request') instead of route() to avoid blocking and AttributeError (Route vs Request)
            page.on("request", intercept_request)
            
            # Use Standard Watch URL with Desktop User Agent
            # This allows cookies to work correctly (First-Party context)
            video_id = url
            if "v=" in url:
                video_id = url.split("v=")[1].split("&")[0]
            elif "youtu.be" in url:
                video_id = url.split("/")[-1]
            elif "embed" in url:
                video_id = url.split("/")[-1].split("?")[0]
                
            target_url = f"https://www.youtube.com/watch?v={video_id}"
            log(f"[Playwright] 正在前往影片頁面 (Desktop Watch Mode): {target_url}")
            
            try:
                # Add stealth script to hide webdriver property
                page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
                
                # Watch page is heavier, give it more time
                page.goto(target_url, timeout=45000, wait_until="domcontentloaded")
            except Exception as e:
                log(f"[Playwright] 頁面載入警告 (嘗試繼續): {e}")
            
            # Dismiss cookie consent if present
            log("[Playwright] 處理 Cookie 同意彈窗...")
            try:
                # Click "Reject all" or "Accept all"
                consent_selectors = [
                    'button[aria-label="Reject all"]',
                    'button:has-text("Reject all")', 
                    'button[aria-label="Accept all"]',
                    'button:has-text("Accept all")',
                    'button:has-text("I agree")',
                    'button:has-text("Agree")',
                    'tp-yt-paper-button:has-text("Accept")',
                    '.eom-button-row button:first-child' # Often the 'I agree' button in Google consent
                ]
                for selector in consent_selectors:
                    if page.is_visible(selector):
                        page.click(selector)
                        log(f"[Playwright] 點擊了同意/拒絕按鈕 ({selector})")
                        page.wait_for_timeout(1000)
                        break
            except Exception as e:
                log(f"[Playwright] Cookie 處理警告: {e}")
            
            # Wait for page to stabilize
            page.wait_for_timeout(2000)
            
            # Check for "Sign in" or Blocked state
            try:
                if page.get_by_text("Sign in to confirm you’re not a bot").is_visible(timeout=2000):
                    log("[Playwright] ⚠️ 偵測到機器人驗證 (Bot Detection)，嘗試繼續但可能失敗...")
                if page.get_by_text("Video unavailable").is_visible(timeout=1000):
                    log("[Playwright] ❌ 影片無法播放 (Video unavailable)")
            except:
                pass

            # Click on video to start playback
            log("[Playwright] 準備啟動播放...")
            try:
                # 0. Wait for video element (Crucial check)
                try:
                    page.wait_for_selector('video', timeout=5000)
                    log("[Playwright] 🎥 找到 <video> 元素")
                except:
                    log("[Playwright] ⚠️ 找不到 <video> 元素，可能被阻擋或尚未載入")

                # 1. Force Play via JavaScript
                log("[Playwright] 嘗試方法 1: JS .play()")
                # Use evaluate_handle to be safer
                page.evaluate("""() => {
                    const v = document.querySelector('video');
                    if (v) { v.muted = false; v.play().catch(e => console.error(e)); }
                }""")
                page.wait_for_timeout(1000)

                # 2. Click Large Play Button (Specific to Embeds)
                if page.is_visible('.ytp-large-play-button'):
                    log("[Playwright] 嘗試方法 2: 點擊中央大播放鈕 (.ytp-large-play-button)")
                    page.click('.ytp-large-play-button', force=True)
                    page.wait_for_timeout(1000)

                # 3. Click center of screen
                log("[Playwright] 嘗試方法 3: 點擊畫面中心")
                viewport_size = page.viewport_size
                if viewport_size:
                    page.mouse.click(viewport_size['width'] / 2, viewport_size['height'] / 2)
                    page.wait_for_timeout(1000)
                    
                # 4. YTP Play button (Bottom bar)
                if page.is_visible('.ytp-play-button'):
                    log("[Playwright] 嘗試方法 4: 點擊底部播放按鈕")
                    page.click('.ytp-play-button')
                    page.wait_for_timeout(1000)
                
                # 5. Keyboard shortcuts
                log("[Playwright] 嘗試方法 5: 鍵盤 'Space/k'")
                page.keyboard.press('k')
                page.wait_for_timeout(500)
                page.keyboard.press('Space')
                page.wait_for_timeout(1000)

            except Exception as e:
                log(f"[Playwright] 播放嘗試警告: {e}")
            
            # Wait longer for audio to buffer (30s)
            log("[Playwright] 等待音訊緩衝 (30s)...")
            # Loop check for urls
            for i in range(30):
                if audio_urls:
                    log(f"[Playwright] ✅ 成功抓取音訊 URL ({len(audio_urls)} 個)")
                    break
                
                # Periodic status check
                if i % 5 == 0 and i > 0:
                    log(f"[Playwright] ...等待中 ({i}s)")
                
                page.wait_for_timeout(1000)
            
            if not audio_urls:
                log("[Playwright] ❌ 未捕獲到音訊，正在截圖留存 (snapshot_failed.png)...")
                try:
                    page.screenshot(path="snapshot_failed.png")
                except Exception as e:
                    log(f"[Playwright] 截圖失敗: {e}")

            browser.close()
        
        if not audio_urls:
            log("[Playwright] 未捕獲到任何音訊 URL")
            return None
        
        # Download the first captured audio URL
        audio_url = audio_urls[0]
        log(f"[Playwright] 正在下載音訊...")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://www.youtube.com/'
        }
        
        response = requests.get(audio_url, headers=headers, stream=True, timeout=120)
        response.raise_for_status()
        
        with open(output_file, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        log(f"[Playwright] 音訊下載完成: {output_file}")
        return output_file
        
    except Exception as e:
        log(f"[Playwright] 錯誤: {e}")
        return None

def get_audio_and_transcribe(url):
    """Downloads audio via yt-dlp and transcribes via Whisper."""
    import subprocess
    
    log("\n[Fallback] 找不到逐字稿。嘗試進行語音轉錄 (Whisper)...")
    
    # 1. Download audio using yt-dlp
    output_filename = "temp_audio" # yt-dlp adds extension
    
    # Clean up previous temp files
    if os.path.exists(output_filename + ".m4a"):
        os.remove(output_filename + ".m4a")
    if os.path.exists(output_filename + ".webm"):
        os.remove(output_filename + ".webm")
        
    log("使用 yt-dlp 下載音訊中...")
    try:
        opts = get_yt_dlp_opts()
        opts['outtmpl'] = output_filename + ".%(ext)s"
        
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])
            
        # Find which file was downloaded
        if os.path.exists(output_filename + ".m4a"):
            output_filename += ".m4a"
        elif os.path.exists(output_filename + ".webm"):
            output_filename += ".webm"
        else:
            # Fallback check
            files = [f for f in os.listdir('.') if f.startswith("temp_audio.")]
            if files:
                output_filename = files[0]
            else:
                 # CRITICAL FIX: Raise exception instead of returning None to trigger Playwright fallback
                 raise Exception("下載後找不到音訊檔案 (File Not Found)")

        log(f"下載完成: {output_filename}")
        
        # Check file size (OpenAI limit: 25MB)
        file_size_mb = os.path.getsize(output_filename) / (1024 * 1024)
        log(f"檔案大小: {file_size_mb:.2f} MB")
        
        if file_size_mb > 24: # Leave some buffer
            log("檔案過大，無法使用 Whisper API (>25MB)。正在壓縮...")
            compressed_filename = "temp_audio_compressed.mp3"
            
            # Clean up prev compressed
            if os.path.exists(compressed_filename):
                os.remove(compressed_filename)
                
            # Compress using ffmpeg with dynamic bitrate
            # Attempt 8k bitrate + mono for maximum compression
            ffmpeg_cmd = [
                "ffmpeg", "-i", output_filename,
                "-vn", # No video
                "-ac", "1", # Force Mono
                "-b:a", "8k", 
                "-y", # Overwrite
                compressed_filename
            ]
            
            try:
                subprocess.run(ffmpeg_cmd, check=True, capture_output=True)
                log(f"壓縮完成: {compressed_filename}")
                
                # Verify new size
                new_size = os.path.getsize(compressed_filename) / (1024 * 1024)
                log(f"新檔案大小: {new_size:.2f} MB")
                
                if new_size > 25:
                    log("警告：壓縮後的檔案仍然 > 25MB。Whisper API 可能會失敗。建議進行分割 (尚未實作)。")

                # Cleanup original
                os.remove(output_filename)
                output_filename = compressed_filename
                
            except subprocess.CalledProcessError as e:
                log(f"壓縮音訊時發生錯誤: {e}")
                log(f"Stderr: {e.stderr}")
                return None
        
    except Exception as e:
        log(f"使用 yt-dlp 下載音訊時發生錯誤: {e}")
        log("[yt-dlp 失敗] 嘗試使用 Playwright 瀏覽器下載...")
        
        # FALLBACK: Use Playwright browser to capture audio
        playwright_file = download_audio_playwright(url)
        if playwright_file and os.path.exists(playwright_file):
            output_filename = playwright_file
            log(f"[Playwright] 成功，使用檔案: {output_filename}")
        else:
            log("[Playwright] 也失敗了，無法取得音訊檔案。")
            return None
        
    if not os.path.exists(output_filename):
        log("錯誤：下載後找不到音訊檔案。")
        return None
        
    # 2. Transcribe with Whisper
    log("正在轉錄音訊 (這可能需要一點時間)...")
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        log("錯誤：遺失 OPENAI_API_KEY。")
        return None
        
    client = openai.OpenAI(api_key=api_key)
    
    # Check size again
    final_size_mb = os.path.getsize(output_filename) / (1024 * 1024)
    
    transcripts = []
    files_to_process = []
    
    if final_size_mb > 24:
        log(f"檔案仍然過大 ({final_size_mb:.2f} MB)。正在分割成多個片段...")
        # Split into 20-minute chunks (should be safe for 16k/8k bitrate)
        # 20 mins * 60 sec * 16kbit/8 = 2.4 MB. Very safe.
        # Even at 128k, 20 mins is ~19MB.
        chunk_pattern = "temp_audio_chunk_%03d.mp3"
        subprocess.run([
            "ffmpeg", "-i", output_filename,
            "-f", "segment",
            "-segment_time", "1200", # 20 minutes
            "-c", "copy",
            chunk_pattern,
            "-y"
        ], check=True, stderr=subprocess.DEVNULL)
        
        # Collect chunks
        import glob
        files_to_process = sorted(glob.glob("temp_audio_chunk_*.mp3"))
        log(f"已分割成 {len(files_to_process)} 個片段。")
    else:
        files_to_process = [output_filename]

    try:
        # Calculate audio duration for cost tracking
        try:
            duration_cmd = [
                "ffprobe", 
                "-v", "error", 
                "-show_entries", "format=duration", 
                "-of", "default=noprint_wrappers=1:nokey=1", 
                output_filename # Use file before splitting for total duration check? No, we process chunks.
            ]
            
            # If we split, we should track cost per chunk or total original file?
            # It's better to track based on what we send to Whisper.
            # But here we loop through files_to_process.
            pass
        except:
            pass

        full_transcript = ""
        total_duration = 0.0

        for audio_file_path in files_to_process:
            log(f"正在轉錄 {audio_file_path}...")
            
            # Get duration of this chunk
            chunk_duration = 0.0
            try:
                out = subprocess.check_output([
                    "ffprobe", "-v", "error", "-show_entries", "format=duration", 
                    "-of", "default=noprint_wrappers=1:nokey=1", audio_file_path
                ]).strip()
                chunk_duration = float(out)
                total_duration += chunk_duration
            except Exception as e:
                log(f"Warning: Could not determine audio duration for cost tracking: {e}")
            
            with open(audio_file_path, "rb") as audio_file:
                chunk_transcript = client.audio.transcriptions.create(
                    model="whisper-1", 
                    file=audio_file,
                    response_format="text"
                )
                full_transcript += chunk_transcript + " "
            
            # Clean up chunk
            if audio_file_path != output_filename:
                os.remove(audio_file_path)
            
            # Track cost for this chunk
            if chunk_duration > 0:
               cost_tracker.track_audio(chunk_duration)

        log(f"Whisper 轉錄完成。總時長: {total_duration:.2f} 秒。預估成本: ${cost_tracker.get_total_cost():.4f} (本月累積)")

        # Clean up original
        if os.path.exists(output_filename):
            os.remove(output_filename)
            
        return full_transcript
        
    except Exception as e:
        log(f"Whisper 轉錄過程中發生錯誤: {e}")
        return None
