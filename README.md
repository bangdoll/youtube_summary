# Youtube Intelligence Web App

將 Youtube 影片內容轉化為可執行的結構化智慧筆記。

![UI Preview](https://github.com/bangdoll/youtube_summary/assets/placeholder/preview.png)

## ✨ 功能亮點

- **Premium UI**: 採用深色玻璃擬態 (Glassmorphism) 設計，視覺體驗升級。
- **Real-time Console**: 內建即時終端機，即時顯示下載與分析進度。
- **Streaming Intelligence**: 透過 Server-Sent Events (SSE) 技術，無需重新整理頁面。
- **Markdown Render**: 分析結果直接渲染為精美排版的文件，支援一鍵複製與下載。
- **完全繁體中文**: 全介面在地化。

## 🛠 安裝與啟動

### 前置需求
- Python 3.8+
- OpenAI API Key

### 安裝步驟

1. **複製專案**
   ```bash
   git clone https://github.com/bangdoll/youtube_summary.git
   cd youtube_summary
   ```

2. **安裝套件**
   ```bash
   pip install -r requirements.txt
   # 確保包含: fastapi, uvicorn, python-multipart, youtube-transcript-api, openai, pytubefix
   ```
   *注意：若 `requirements.txt` 尚未完整，請手動安裝：*
   ```bash
   pip install fastapi uvicorn python-multipart youtube-transcript-api openai pytubefix
   ```

3. **環境設定**
   建立 `.env` 檔案並填入您的 API Key：
   ```bash
   # .env
   OPENAI_API_KEY=sk-your-api-key-here
   ```

4. **啟動伺服器**
   ```bash
   python3 -m uvicorn main:app --reload
   ```

5. **使用**
   打開瀏覽器訪問 [http://localhost:8000](http://localhost:8000)。

## 📂 專案結構

- `main.py`: FastAPI 後端伺服器 (Web Server)。
- `youtube_summary.py`: 核心邏輯 (Youtube 下載、轉錄、GPT 分析)。
- `web/`: 前端資源 (HTML/CSS/JS)。
- `prompts/`: AI 提示詞模板。
