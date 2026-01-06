# CHANGELOG

## [2.1.0] - 2026-01-06

### 🌟 介面與功能大改版 (Vibe Coding Update)

#### 新增功能
- **智慧成本監控 (Cost Monitoring)**：
    - 追蹤 GPT-4o Token 與 Whisper 分鐘數。
    - 實作每月 $20 USD 預算警示系統。
    - 整合 **Firebase Realtime Database** 實現雲端數據持久化 (Persistence)。
- **全新 Landing Page**:
    - 採用 "Vibe Coding" 設計語彙 (深色玻璃擬態、動態網格)。
    - 新增 **Features Grid** (Gemini 3.0, Security, Cost, Structured Output)。
    - 新增 **NotebookLM 對比專區** (強調客製化、數據主權、自動化)。
- **生態系整合**: 優化 Markdown 輸出格式，支援 **Heptabase / Obsidian / Notion**。
- **UX 優化**: 將「執行日誌」移至輸入框正下方，提供更直覺的操作回饋。

#### 優化調整
- 升級核心說明為 **Gemini 3.0**。
- 將所有使用者介面與文案統一為**繁體中文**。
- 優化 SSE 連線穩定性與錯誤處理。

---

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
