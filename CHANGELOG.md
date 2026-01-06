# CHANGELOG

## [2.0.0] - 2026-01-06

### 🚀 重大更新：Gemini 直接分析 YouTube 影片

#### 新增功能
- **Gemini 2.5 Flash 整合**：直接「觀看」YouTube 影片並生成摘要，**完全繞過 Bot 偵測問題**
- **新增 `GOOGLE_API_KEY` 環境變數**：用於 Gemini API 認證
- **智慧分析優先級**：Gemini 分析 → 逐字稿分析 (備用)

#### 修復問題
- ❌ 修復 Render/Vercel 伺服器 IP 被 YouTube 標記為 Bot 的問題
- ❌ 移除已棄用的 OAuth 認證代碼
- ❌ 切換 SDK 從 `google-generativeai` 到 `google-genai`

#### 技術變更
- 新增 `analyze_with_gemini()` 函數
- 更新 `requirements.txt`：新增 `google-genai`、`yt-dlp`、`playwright`
- 更新 `process_video_pipeline()` 優先使用 Gemini

---

## [1.0.0] - 2026-01-05

### 初始版本
- FastAPI Web 伺服器
- 即時終端機日誌 (SSE)
- Markdown 渲染
- OpenAI GPT-4o 分析
- YouTube 逐字稿擷取
- Whisper 語音轉錄備用方案
