import streamlit as st
import sys
import io
import os
import time
from contextlib import redirect_stdout

# Import core logic
import youtube_summary

st.set_page_config(page_title="Youtube 2 Note", page_icon="📝", layout="wide")

st.title("🎥 Youtube 轉筆記 AI 助手")
st.markdown("""
輸入 Youtube 連結，自動執行：
1. **下載逐字稿** (或自動聽打)
2. **AI 深度分析**
3. **生成 Markdown 筆記**
""")

# Input
url = st.text_input("Youtube URL", placeholder="https://www.youtube.com/watch?v=...")

# Custom Logger to capture print output and display in Streamlit
class StreamlitLogger:
    def __init__(self, container):
        self.container = container
        self.buffer = []
        
    def write(self, text):
        # Pass to standard stdout so we see it in terminal
        sys.__stdout__.write(text)
        
        # Add to buffer if not just newline (to avoid empty updates)
        if text.strip():
            # Append line with timestamp? No, keep simple.
            self.buffer.append(text.strip())
            # Keep only last 10 lines for cleaner display in status
            recent_logs = "\n".join(self.buffer[-15:])
            self.container.code(recent_logs, language="text")
            
    def flush(self):
        sys.__stdout__.flush()

if st.button("🚀 開始分析", type="primary"):
    if not url:
        st.error("請輸入 Youtube 網址！")
    else:
        # Layout
        status_col, result_col = st.columns([1, 1])
        
        with status_col:
            st.subheader("⚙️ 執行進度")
            status_box = st.empty()
            log_expander = st.expander("查看詳細日誌", expanded=True)
            with log_expander:
                log_container = st.empty()

        # Redirect stdout
        old_stdout = sys.stdout
        logger = StreamlitLogger(log_container)
        sys.stdout = logger
        
        try:
            status_box.info("系統啟動中...")
            
            # Run Pipeline
            with st.spinner("正在努力看影片中... (如果是長影片請耐心等待 ☕️)"):
                filename, content = youtube_summary.process_video_pipeline(url)
            
            status_box.success("✅ 完成！")
            
            with result_col:
                st.subheader("📝 筆記預覽")
                # Show download button first
                with open(filename, "r", encoding="utf-8") as f:
                    file_data = f.read()
                    st.download_button(
                        label="📥 下載 Markdown 筆記",
                        data=file_data,
                        file_name=os.path.basename(filename),
                        mime="text/markdown"
                    )
                st.markdown("---")
                st.markdown(content)
                
        except Exception as e:
            status_box.error("❌ 任務失敗")
            st.error(f"發生錯誤: {e}")
            # Show full logs on error
            st.code("\n".join(logger.buffer))
            
        finally:
            # Restore stdout
            sys.stdout = old_stdout
