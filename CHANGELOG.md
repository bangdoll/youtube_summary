# CHANGELOG


## [2.6.0] - 2026-01-10

### 🎨 NoteSlide 像素級重建 (Pixel-Perfect Reconstruction)

#### ✨ AI 圖片文字移除 (AI Text Removal)
- **Gemini Imagen 整合**：使用 **Nano Banana Pro** (`gemini-3-pro-image-preview`) 進行圖片編輯。
- **智慧文字擦除**：AI 自動偵測並移除圖片上的所有文字（標題、標籤、數字等）。
- **無縫填補**：使用 content-aware fill 技術，以周圍背景顏色/紋理自然填補文字區域。
- **圖文分離**：生成的 PPTX 中，圖片為「乾淨版」，文字則作為獨立可編輯的文字框呈現。

#### 📐 NoteSlide 風格 OCR 精確定位 (Stage 1)
- **text_elements 陣列**：Gemini 現在會偵測每個文字區塊並回傳精確邊界框 `[ymin, xmin, ymax, xmax]`。
- **字體屬性還原**：保留字體大小 (pt)、粗體狀態、文字顏色 (hex)。
- **精確 Shape 定位**：每個文字區塊使用 OCR 偵測到的精確位置建立獨立 PowerPoint Shape。
- **visual_elements 偵測**：偵測所有視覺元素 (圖片/圖表/圖示) 並回傳邊界框。

#### 🎯 圖片邊界框偵測優化 (Improved Bounding Box Detection)
- **英文提示詞**：所有 Gemini 提示改為英文以提升 AI 理解精度。
- **緊密裁切**：強調只留 10-20 像素邊距，精準切割單一圖片。
- **排除文字區域**：明確指示排除標題、Bullet Points、頁碼、Logo 等。
- **多圖處理**：若頁面有多個視覺元素，自動選擇最大的。

### 🐛 錯誤修復 (Bug Fixes)

#### 🔧 前端修復
- **修復 PDF 上傳功能**：恢復遺失的全域函式 (`triggerUpload`, `handleFileSelect`, `startPreview` 等)。
- **修復設定按鈕**：恢復遺失的 `openSettings`, `closeSettings`, `saveSettings` 函式。
- **修復複製/下載按鈕**：在 YouTube 分析結果頁恢復「複製內容」與「下載 Markdown」按鈕。
- **移除錯誤按鈕**：從 YouTube 分析結果頁移除不適用的「生成簡報」按鈕。

#### 📦 PPTX 下載修復
- **修復下載檔名**：改進 `Content-Disposition` 標頭解析邏輯，確保下載的 PPTX 檔案有正確的 `.pptx` 副檔名。
- **備用檔名邏輯**：若標頭解析失敗，自動使用原始 PDF 檔名作為 PPTX 檔名。

### 📚 技術細節
- **模型升級**：文字移除功能使用 `gemini-3-pro-image-preview` (Nano Banana Pro)。
- **API 節流**：因雙倍 API 呼叫 (分析 + 文字移除)，間隔從 2 秒增加到 3 秒。
- **備用機制**：若 Gemini 圖像編輯不可用或 OCR 未回傳 `text_elements`，自動使用傳統版面。

---

## [2.5.1] - 2026-01-09

### 📊 NoteSlide 體驗重大升級 (Legacy Upgrade)

#### ✨ Codia 風格 UI 重構
- **網格預覽視圖 (Grid View)**：上傳 PDF 後不再盲目生成，新增「網格預覽」步驟。
- **可視化選擇**：直觀查看每一頁的縮圖，並支援「全選/取消全選」功能，精準選擇要轉換的頁面。
- **流程優化**：改為「上傳 -> 預覽 -> 調整 -> 生成」的更專業工作流，徹底解決傳統單鍵生成的體驗問題。

#### 🎨 智慧動態版型 (Dynamic Layouts)
- **版型感知引擎**：後端 Gemini Prompt 升級為「簡報設計顧問」角色，能根據頁面內容（圖表 vs 文字）自動選擇最佳版型。
- **全寬模式 (Full Width)**：針對裝飾性圖片或文字量大的頁面，自動隱藏圖片並切換為全寬文字排版。
- **分割模式 (Split Layout)**：針對圖表密集的分析頁面，保留經典的左圖右文佈局。
- **更深層的洞察**：AI 指令優化，專注於提取「核心價值」與「商業行動建議」。


### 🔓 開放架構與 BYOK (Public Access & BYOK)

#### 🚀 全面開放首頁 (Public Homepage)
- **移除登入限制**：首頁不再強制要求 Google 登入，「Youtube 智慧大腦」現在對所有訪客開放。
- **BYOK (Bring Your Own Key) 模式**：訪客可直接使用自己的 **Google Gemini** 或 **OpenAI** API Key 進行分析。金鑰僅儲存於本地瀏覽器 (localStorage)，伺服器不保存，確保隱私與配額安全。
- **無縫體驗**：不需要任何帳號註冊，隨開隨用，如同使用線上工具般便捷。

#### ⚙️ 設定功能升級 (New Settings UI)
- **自訂金鑰管理**：在右上角新增永久顯示的「⚙️ 設定」按鈕，方便用戶隨時輸入或更新 API Key。
- **申請引導連結**：在輸入框下方新增「取得 API Key」的官方連結，引導新用戶快速申請 Google AI Studio 或 OpenAI Platform 金鑰。
- **介面優化**：重構頂部導航列 (Top Nav)，確保設定按鈕在任何狀態下皆可見，使用者資訊則僅在登入後顯示。

#### 🔄 CI/CD 自動化 (Automated Deployment)
- **GitHub Actions**：建立 `.github/workflows/deploy.yml`，支援推送到 `main` 分支時自動構建 Docker Image 並部署至 Google Cloud Run。

#### 🆕 品牌重塑 (Rebranding)
- **Second Brain OS**：專案正式更名為「Second Brain OS (第二大腦作業系統)」，以反映更強大的多模態處理能力 (影片 + 文件)。

#### 📊 NoteSlide 簡報生成 (PowerPoint Generator)
- **PDF 轉 PPTX**：新增模式切換分頁，支援上傳 NotebookLM 輸出或任何 PDF 文件。
- **Gemini Vision 識別**：利用多模態視覺模型識別每一頁的標題、內文重點與版面配置。
- **一鍵下載**：自動生成包含演講者備忘錄的 `.pptx` 簡報檔，完美還原內容架構。

### 🐛 錯誤修復 (Bug Fixes)
- **修復介面消失問題**：修正前端腳本 (`script.js`) 的語法錯誤，解決輸入介面因執行錯誤而無法顯示的問題。
- **修復按鈕可見性**：修正設定按鈕被隱藏在使用者區塊內的問題，將其獨立至永久可見區域。
- **資料更正**：更新開發者簡介與大頭照，並新增個人網站連結。

---

## [2.4.0] - 2026-01-07

### 🚀 重大功能發布 (Major Features)

#### 🎥 長影片解析支援 (Long Video Support)
- **Audio Fallback 機制**：針對超過 3 小時或 10800 幀的超長影片，系統現在會自動從「視覺模式」切換為「聽覺模式」。自動下載音訊並上傳至 Gemini 進行全量分析，突破 API 限制。
- **PO Token 整合 (Bot Defense Penetration)**：整合 `pytubefix` 生成 Proof of Origin Token，成功繞過 YouTube 的 "Sign in to confirm you're not a bot" 驗證，大幅提升音訊下載成功率。

#### 📱 PWA 行動裝置體驗 (Mobile Experience)
- **App Icon 與主畫面支援**：新增 PWA Meta Tags 與高質感霓虹風格圖示 (Icon)。現在您可以將網頁「加入主畫面」，獲得如同原生 App 的全螢幕沈浸體驗。
- **UI 優化**：針對行動裝置介面微調，並更新了開發者大頭照。

#### ⚡ 首頁互動體驗 (Live Demo)
- **30秒 Live Terminal Demo**：在未登入的首頁新增純 CSS/JS 驅動的模擬終端機動畫，動態展示 AI 分析流程，取代靜態的 "LIVE DEMO" 圖片，提升科技感 (Vibe Coding)。

### 🐛 錯誤修復與優化 (Fixes & Improvements)
- **UI 高對比優化**：強化「分析中」按鈕樣式，加入旋轉動畫 (Spinner) 與光暈效果，並提升字體對比度，讓狀態回饋更清晰。
- **修復 NameError**：修正 `youtube_summary.py` 中因執行順序導致的 `get_audio_and_transcribe` 未定義錯誤。
- **修復 403 Forbidden**：確保 `yt-dlp` 正確讀取 Cookie 以解決部分影片的 403 下載錯誤。

---

## [2.3.0] - 2026-01-06

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
