# NoteSlide 品質優化與編輯器任務

## 階段一：禁用 OCR 定位 (已完成)
- [x] 禁用 `text_elements` 邊界框定位
- [x] 強制使用分割佈局

## 階段二：優化分割佈局 (已完成)
- [x] 左側 50% 放置清理後圖片
- [x] 右側 50% 放置標題與條列要點
- [x] 使用標準字體大小和間距

## 階段三：改進 Gemini 提示 (已完成)
- [x] 簡化回傳格式 (標題、條列要點)
- [x] 移除邊界框相關要求

## 階段四：網頁簡報內容編輯器 (已完成)
- [x] 後端：重構 `slide_generator.py`，分離分析與生成
- [x] 後端：新增 `POST /api/analyze-slides` (回傳 JSON 與圖片網址)
- [x] 後端：新增 `POST /api/generate-slides` (接收 JSON 輸出 PPTX)
- [x] 前端：新增編輯模式按鈕 (整合至生成流程)
- [x] 前端：實作投影片編輯器介面
- [x] 前端：實作下載流程

## 驗證與部署
- [x] 本地測試 (自動化子代理驗證通過)
- [x] 更新變更日誌
- [x] 推送至 GitHub
- [x] Cloud Run 部署 (透過 GitHub Actions 自動化)

## 維運任務 (v2.10.20)
- [x] 後端：修復逾時處理器中的 PIL 匯入錯誤 (防止 0% 卡住崩潰)
- [x] 後端：修復 0 位元組檔案上傳錯誤 (重複讀取) 於 `main.py`
- [x] 介面：預設選中「移除 NotebookLM 圖標」(已確認預設勾選)
- [x] 介面：調整「選擇檔案」按鈕避免壓到虛線邊框 (已新增邊距修正)
- [x] 介面：新增即時日誌終端機至「準備中...」覆蓋層
- [x] 介面：置中檔案上傳視窗
- [x] 驗證：介面修復驗證通過（選擇檔案按鈕未壓線、預設勾選正確）
- [x] 修復：`generateSlides` 函數變數未定義錯誤 (file/geminiKey/selectedIndices)
- [x] 驗證：完整 PDF 上傳流程測試（已由用戶確認：顯示正確）
- [x] 研究：分析外部參考程式碼以供未來功能整合

## v2.10.21 (Current)
- [x] 修復：進度條樣式缺失 (CSS Variable)
- [x] 修復：Cloud Run 圖片 404 (實作 Base64 Stateless 傳輸)
- [x] 優化：提升圖片去字品質 (DPI 200 + Prompt 強化)
- [x] 優化：Payload 傳輸壓縮 (Max 1600px + JPEG 80%)
- [x] 修復：UI 按鈕點擊判定 (onmousedown -> onclick)

## v2.10.22 (Stability)
- [x] 優化：Sequential Processing (先分析後修圖) 解決 Rate Limit
- [x] 優化：Smart Resize v2 (1024px Analysis / 1600px Edit)
- [x] 修復：Fail-Safe PPTX Generation (容許單頁失敗，保證產出)
- [x] 修復：Duplicate Logs (解決日誌重複問題)
- [x] 修復：Fixed API (422 Schema Mismatch / camelCase -> snake_case)
- [x] UX：分析完成與預覽生成後自動捲動 (Auto Scroll All)

## v3.0.0 (原生混合架構)
- [x] 核心：原生 PDF 文字提取 (`native_pdf.py`)
- [x] 核心：確定性遮罩引擎 (`mask_engine.py`)
- [x] 整合：混合流水線 (`slide_generator.py`)
- [x] 整合：智慧修補 (Gemini 編輯)
- [x] 驗證：零文字殘留與完美文字準確度

## v3.0.1 (穩定性修正與 UX 優化)
- [x] 核心：First Page Probe (首頁探針) 機制，防止失敗時浪費 API 成本
- [x] 介面：修正「設定 API Key」按鈕垂直置中與樣式
- [x] 介面：修正進度條訊息格式 (顯示「第 X/Y 頁」)
- [x] 介面：修正按鈕需點擊兩次的問題 (onclick -> onmousedown)
- [x] 驗證：確保下載的 PPTX 為可編輯的原生格式
- [x] 驗證：確保下載檔名正確 (原始檔名.pptx)

## v4.0.0 (Native Vector Stripping)
- [x] 依賴：安裝 `pymupdf` 並更新 `requirements.txt`
- [x] 核心：重構 `native_pdf.py` 使用 PyMuPDF 實作 `get_clean_image` (向量去字)
- [x] 核心：確保掃描檔 Fallback 機制保留
- [x] 整合：修改 `slide_generator.py` 優先使用向量去字路徑
- [x] 驗證：測試原生 PDF 背景，確認 100% 無文字殘留且無需 Inpainting
- [x] 驗證：確認複雜背景 (漸層/圖表) 未受損 (經由合成 PDF 驗證)

## v5.0.0 (Layout Reconstruction) - Current
- [x] 核心：修改 `analyze_slide_with_gemini` Prompt，請求 `bbox` 與 `font_size`
- [x] 核心：更新 `process_single_page` 以傳遞 Native BBox (Native Path) 或 Vision BBox (Scanned Path)
- [x] 引擎：重構 `create_pptx_from_analysis` 支援 `overlay` 佈局與絕對座標定位
- [x] 驗證：針對 `Awakening_Blueprint.pdf` (Scanned) 測試 Vision 重建效果 (v5.0.0 Overlay 驗證通過)
- [x] 驗證：針對原生 PDF 測試 Native 重建效果 (確認文字對齊)
- [x] **[Hotfix]** 修復 `OSError: image file is truncated` (v5.0.1)
- [x] 驗證 Cloud Run 日誌狀態 (正常)
- [x] 確認 Vercel 斷開連結 (僅 Cloud Run 運作中)

## v5.1.0 序列視覺流水線 (Sequential Vision Pipeline)
- [x] 重構：混合序列處理 (分析 -> 遮罩 -> 修補)
- [x] 修復：掃描 PDF 的殘影文字移除

## v5.2.0 強力遮罩模式 (Aggressive Masking)
- [x] 調校：將遮罩填充增加至 15px 以獲得更好的覆蓋率

## v5.3.0 智慧局部採樣 (Smart Local Sampling)
- [x] 調校：「變色龍遮罩」- 採樣局部背景像素而非全域平均
- [x] 修復：消除白色背景上的灰色方塊偽影 (Gray Box Artifacts)

## v5.4.0 物件提取 (Object Lifting) - Current
- [x] AI：在 Gemini 分析中偵測 `visual_elements` (圖片/圖表)
- [x] 核心：從原始圖像中裁切視覺元素
- [x] 核心：遮罩已提取的視覺元素以生成乾淨背景
- [x] 引擎：將裁切的視覺元素作為獨立的圖片物件放置在 PPTX 中
- [x] 驗證：確認 Cloud Run 部署 (Commit `ca6fc56`)
- [ ] 驗證：確認最終 PPTX 中的物件提取效果 (v5.4.2 優化中)

## v6.0.0 全物件可編輯化 (Full Object Editability) - Planned
- [x] **基礎設施**：新增 `rembg` (u2net) 與 `potrace` 至 Docker/Requirements
- [x] **功能**：透明物件提取 (使用去背取代矩形裁切)
- [ ] **功能**：藍圖向量化 (點陣圖 -> 向量圖形)
- [/] **研究**：使用 Python 將 SVG/EMF 注入 PPTX 的可行性 (原型 `research_vectorize.py` 已建立)
