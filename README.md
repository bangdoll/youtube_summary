# Youtube Intelligence Web App

將 Youtube 影片內容轉化為可執行的結構化智慧筆記。

## ✨ 功能亮點

- **🤖 Gemini 直接分析**：使用 Google Gemini 2.5 Flash 直接「觀看」YouTube 影片，無需下載！
- **Premium UI**: 採用深色玻璃擬態 (Glassmorphism) 設計，視覺體驗升級。
- **Real-time Console**: 內建即時終端機，即時顯示分析進度。
- **Streaming Intelligence**: 透過 Server-Sent Events (SSE) 技術，無需重新整理頁面。
- **Markdown Render**: 分析結果直接渲染為精美排版的文件，支援一鍵複製與下載。
- **完全繁體中文**: 全介面在地化。

## 🛠 安裝與啟動

### 前置需求
- Python 3.9+
- Google API Key (Gemini)
- OpenAI API Key (備用)

### 安裝步驟

1. **複製專案**
   ```bash
   git clone https://github.com/bangdoll/youtube_summary.git
   cd youtube_summary
   ```

2. **安裝套件**
   ```bash
   pip install -r requirements.txt
   ```

3. **環境設定**
   建立 `.env` 檔案並填入您的 API Key：
   ```bash
   # .env
   GOOGLE_API_KEY=AIza...          # 主要 (Gemini 分析)
   OPENAI_API_KEY=sk-...           # 備用 (逐字稿分析)
   ```

4. **啟動伺服器**
   ```bash
   python3 -m uvicorn main:app --reload
   ```

5. **使用**
   打開瀏覽器訪問 [http://localhost:8000](http://localhost:8000)。

## 🔧 分析流程

```
YouTube URL 
    ↓
[優先] Gemini 2.5 Flash 直接觀看影片
    ↓ (若失敗)
[備用] 逐字稿 API → OpenAI GPT-4o
    ↓
生成結構化 Markdown 筆記
```

## 📂 專案結構

- `main.py`: FastAPI 後端伺服器
- `youtube_summary.py`: 核心邏輯 (Gemini 分析、逐字稿處理)
- `web/`: 前端資源 (HTML/CSS/JS)
- `prompts/`: AI 提示詞模板

## 📝 環境變數

| 變數 | 必要 | 說明 |
|------|------|------|
| `GOOGLE_API_KEY` | ✅ | Google AI Studio API Key |
| `OPENAI_API_KEY` | ⚠️ | 備用逐字稿分析 |

## 📄 License

MIT
