# CHANGELOG

## [2.3.0] - 2026-01-07

### ⚡ 核心與穩定性重大升級 (Stability & Core Upgrade)

#### 🚀 核心升級
- **全面採用 Gemini 3 Flash Preview**：將 AI 核心引擎升級至 `gemini-3-flash-preview`，大幅提升理解能力與回應速度，支援最新的 Google Model 生態。
- **恢復使用 Google GenAI SDK (v2)**：因應模型升級，切換回 `google-genai` 現代化 SDK，以支援最新的 API 特性。

#### 🐛 錯誤修復
- **修復 404/429 API 錯誤**：解決了因模型版本 alias (`1.5-flash`) 導致的 404 錯誤，以及實驗模型 (`exp`) 配額為 0 導致的 429 錯誤。現在使用明確指定的 `models/gemini-3-flash-preview` ID。
- **修復 OAuth 登入迴圈 (Login Failed)**：
    - 新增 `ProxyHeadersMiddleware` 以在 Cloud Run Load Balancer 後方正確識別 HTTPS 請求。
    - 鎖定 `SECRET_KEY`，防止 Container 重啟或 Auto-scaling 導致的使用者 Session 失效。
- **修復下載檔名亂碼**：後端強制淨化檔名 (Sanitization)，移除路徑資訊，解決下載時檔名變成 `_app_..._Notes_` 的問題。
- **增強 Bot Detection 繞過**：Playwright 策略加入 Desktop User-Agent 偽裝與 Stealth Headers，提升備援下載的成功率。

#### ✨ 功能增強
- **新增來源連結**：在生成的 Markdown 筆記中自動附上 `[來源: URL]`，方便回溯原始影片。
- **優化成功訊息**：簡化分析完成後的提示訊息，使其更簡潔易讀。

---

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

## [2.2.0] - 2026-01-06

### ☁️ Cloud Run 遷移與效能大躍進

#### 架構升級
- **遷移至 Google Cloud Run**：徹底解決 Render 冷啟動 (90s+) 問題，實現秒級啟動。
- **Playwright 效能優化**：針對 Cloud Run 強大效能 (2GB RAM) 啟用「完整頁面模式 (Watch Page)」，大幅提升長影片音訊捕獲成功率。
- **安全性回歸**：恢復 `ALLOWED_EMAILS` 白名單機制與 Google OAuth 驗證，保障私人使用權限。

#### 修復與調整
- ✅ 修復 Playwright 在無頭模式下可能被靜音導致無法抓取音訊的問題。
- ✅ Dockerfile 更新支援動態 PORT 注入 (Cloud Run Requirement)。
- ✅ 文件全面更新 (README, Walkthrough) 以反映新架構。

---

## [2.1.0] - 2026-01-06

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
