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

# Load environment variables
load_dotenv()

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
    
    # Path to the executable we found earlier
    cli_path = "/Users/bangdoll/Library/Python/3.9/bin/youtube_transcript_api"
    
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

def analyze_transcript(transcript, video_title="Unknown Video"):
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
        return response.choices[0].message.content
    except Exception as e:
        log(f"呼叫 OpenAI API 時發生錯誤: {e}")
        raise Exception(f"呼叫 OpenAI API 時發生錯誤: {e}")

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
        
    log(f"成功！筆記已儲存至: {filename}")
    return filename


def get_youtube_object(url):
    """
    Helper to initialize YouTube object with potential PO Token / OAuth
    to bypass bot detection (especially on Vercel/Cloud).
    """
    from pytubefix import YouTube
    
    use_po_token = os.getenv("USE_PO_TOKEN", "true").lower() == "true"
    po_token = os.getenv("PO_TOKEN")
    visitor_data = os.getenv("VISITOR_DATA")
    use_oauth = os.getenv("USE_OAUTH", "false").lower() == "true"
    
    log(f"Initializing YouTube object. PO_TOKEN present: {bool(po_token)}")
    
    try:
        # Try initializing with PO Token first (for newer pytubefix)
        return YouTube(
            url, 
            use_po_token=use_po_token, 
            po_token=po_token, 
            visitor_data=visitor_data,
            use_oauth=use_oauth,
            allow_oauth_cache=True
        )
    except TypeError as e:
        if "unexpected keyword argument" in str(e):
            log("偵測到舊版 pytubefix，不支援 po_token。嘗試使用基本模式初始化...")
            # Fallback for older versions or if arguments are wrong
            return YouTube(
                url,
                use_oauth=use_oauth,
                allow_oauth_cache=True
            )
        else:
            raise e
    except Exception as e:
        log(f"Error initializing YouTube object: {e}")
        raise e

def process_video_pipeline(url):
    """Orchestrates the video processing pipeline. Returns (filename, note_content)."""
    video_id = get_video_id(url)
    log(f"處理影片 ID: {video_id}")
    
    # Get Title
    video_title = "未知的影片"
    try:
        yt = get_youtube_object(f"https://www.youtube.com/watch?v={video_id}")
        video_title = yt.title
        log(f"影片標題: {video_title}")
    except Exception as e:
        # Fallback title if pytube fails
        video_title = f"Video_{video_id}"
        log(f"警告：無法取得影片標題 ({e})。繼續執行。")
    
    log("正在取得逐字稿...")
    transcript = get_transcript(video_id)
    
    # === Fallback Logic ===
    if not transcript:
        transcript = get_audio_and_transcribe(url)
        
    if not transcript:
        log("嚴重錯誤：無法透過任何方式取得逐字稿。")
        # Raise exception instead of sys.exit so app can catch it
        raise Exception("嚴重錯誤：無法透過任何方式取得逐字稿。")
    # ======================
    
    log("正在分析內容...")
    analysis = analyze_transcript(transcript, video_title)
    
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

def get_audio_and_transcribe(url):
    """Downloads audio via yt-dlp and transcribes via Whisper."""
    import subprocess
    
    log("\n[Fallback] 找不到逐字稿。嘗試進行語音轉錄 (Whisper)...")
    
    # 1. Download audio using pytubefix (more robust than yt-dlp for now)
    output_filename = "temp_audio.m4a"
    
    # Clean up previous temp file if exists
    if os.path.exists(output_filename):
        os.remove(output_filename)
        
    log("使用 pytubefix 下載音訊中...")
    try:
        yt = get_youtube_object(url)
        audio_stream = yt.streams.get_audio_only()
        if not audio_stream:
            log("錯誤：找不到音訊串流。")
            return None
            
        log(f"找到音訊串流: {audio_stream.subtype}")
        # Explicitly append extension
        output_filename = f"temp_audio.{audio_stream.subtype}"
        downloaded_path = audio_stream.download(filename=output_filename)
        log(f"下載完成: {downloaded_path}")
        output_filename = downloaded_path
        
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
        log(f"使用 pytubefix 下載音訊時發生錯誤: {e}")
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
        full_transcript = ""
        for audio_file_path in files_to_process:
            log(f"正在轉錄 {audio_file_path}...")
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

        # Clean up original
        if os.path.exists(output_filename):
            os.remove(output_filename)
            
        return full_transcript
        
    except Exception as e:
        log(f"Whisper 轉錄過程中發生錯誤: {e}")
        return None
