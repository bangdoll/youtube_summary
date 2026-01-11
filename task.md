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
- [x] UX：分析完成與預覽生成後自動捲動 (Auto Scroll All)
