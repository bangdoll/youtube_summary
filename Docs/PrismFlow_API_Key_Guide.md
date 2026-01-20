# PrismFlow API Key 新手教學指南

> **一行摘要**：取得免費的 Google Gemini API Key，瞬間解鎖 PrismFlow 的 100% 影片分析與投影片生成火力。

---

## 🔑 為什麼需要 API Key？

PrismFlow 的核心依賴於 Google 最先進的 **Gemini 3 Flash** AI 模型來進行：
1.  **深度影片聽打與摘要** (Youtube Summary)
2.  **視覺化簡報生成** (NoteFlux)

雖然系統內建了共用的伺服器額度，但為了確保**最快速度**、**最高隱私**以及**不受限制的使用量**，我們強烈建議使用者配置自己的 API Key (BYOK - Bring Your Own Key) 模式。

特別是 **YouTube 智慧分析** 功能，採用了雙引擎架構以確保最高成功率：
*   **優先引擎 (Gemini)**：直接視覺化觀看影片，理解力最強。
*   **備援引擎 (OpenAI)**：當 Gemini 遇上地區限制或讀取失敗時，系統會自動切換至 OpenAI GPT-4o 模型分析逐字稿。

**因此，建議同時填入兩個 API Key 以獲得 100% 的系統穩定度！**

---

## 🚀 Step 1: 取得免費金鑰 (30秒)

1.  開啟 **[Google AI Studio](https://aistudio.google.com/app/apikey)** 網站。
2.  點擊左上角的 **"Create API key"** (建立 API 金鑰) 按鈕。
3.  選擇 **"Create API key in new project"** (在新專案中建立)。
4.  系統會產生一串以 `AIza` 開頭的亂碼，這就是你的鑰匙。
5.  **複製它！** (並妥善保存，不要貼給別人)。

> **💡 小知識**：目前的免費層級 (Free Tier) 允許每分鐘 15 次請求，每天 1,500 次請求，對於個人使用綽綽有餘！

---

## 🤖 Step 2: 取得 OpenAI API Key (選填，強烈建議)

雖然是選填，但為了避免「影片無法讀取」的狀況，建議準備一個 OpenAI Key 作為強大的備援。

1.  登入 **[OpenAI Platform](https://platform.openai.com/api-keys)**。
2.  點擊 **"Create new secret key"**。
3.  設定一個名稱 (例如 PrismFlow)，點擊確認。
4.  **複製 `sk-...` 開頭的密鑰**。

> **注意**：OpenAI API 是**付費服務** (需綁定信用卡)，但費用極低 (分析一部 20 分鐘影片通常不到 $0.05 美金)。

---

## ⚙️ Step 3: 在 PrismFlow 中設定

回到 PrismFlow 網頁介面：

1.  點擊介面右上角的 **"設定" (Settings)** 或 **"🔑"** 圖示。
2.  找到 **"Google Gemini API Key"** 欄位，貼上 `AIza...` 金鑰。
3.  找到 **"OpenAI API Key"** 欄位，貼上 `sk-...` 金鑰。
4.  系統會自動儲存 (或點擊確認)。

---

## ✅ Step 4: 開始使用

現在，當你執行任務時，系統將優先使用你的專屬通道：

*   **雙引擎分析**：Gemini 優先視讀，失敗時自動切換 OpenAI 閱讀逐字稿，確保任務必定完成。
*   **投影片生成**：圖片分析與版面配置的速度將顯著提升。
*   **隱私保障**：你的資料直接傳輸至 Google API，不經過第三方中轉。

---

## ❓ 常見問題 (FAQ)

### Q: 這會收費嗎？
**A: 不會**，除非你手動在 Google Cloud Console 綁定信用卡並開啟付費功能。預設的 Free Tier 是完全免費的，用完也只是暫時暫停，不會扣款。

### Q: 兩個 Key 都要填嗎？
**A:** **建議都填。** 只填 Gemini 也可以運作，但遇到無法直接「看」的影片時會失敗；填了 OpenAI 就能自動補位，讓體驗如絲般順滑。

### Q: Key 會過期嗎？
**A:** 通常不會，除非你手動刪除它。建議每半年檢查一次。

### Q: 使用我的 Key 安全嗎？
**A:** PrismFlow 採用 `BYOK` (Bring Your Own Key) 架構，金鑰僅在發送請求時使用，若是自架版 (Self-hosted) 則完全掌握在你手中。

---

*最後更新：2026-01-20 (v7.2.1)*
