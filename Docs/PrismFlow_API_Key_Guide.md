# PrismFlow API Key 新手教學指南

> **一行摘要**：取得免費的 Google Gemini API Key，瞬間解鎖 PrismFlow 的 100% 影片分析與投影片生成火力。

---

## 🔑 為什麼需要 API Key？

PrismFlow 的核心依賴於 Google 最先進的 **Gemini 1.5 Pro/Flash** AI 模型來進行：
1.  **深度影片聽打與摘要** (Youtube Summary)
2.  **視覺化簡報生成** (NoteSlide)

雖然系統內建了共用的伺服器額度，但為了確保**最快速度**、**最高隱私**以及**不受限制的使用量**，我們強烈建議使用者配置自己的 API Key (BYOK - Bring Your Own Key) 模式。

**好消息是：Google 目前提供非常大方的免費額度！**

---

## 🚀 Step 1: 取得免費金鑰 (30秒)

1.  開啟 **[Google AI Studio](https://aistudio.google.com/app/apikey)** 網站。
2.  點擊左上角的 **"Create API key"** (建立 API 金鑰) 按鈕。
3.  選擇 **"Create API key in new project"** (在新專案中建立)。
4.  系統會產生一串以 `AIza` 開頭的亂碼，這就是你的鑰匙。
5.  **複製它！** (並妥善保存，不要貼給別人)。

> **💡 小知識**：目前的免費層級 (Free Tier) 允許每分鐘 15 次請求，每天 1,500 次請求，對於個人使用綽綽有餘！

---

## ⚙️ Step 2: 在 PrismFlow 中設定

回到 PrismFlow 網頁介面：

1.  點擊介面右上角的 **"設定" (Settings)** 或 **"🔑"** 圖示。
2.  找到 **"Google Gemini API Key"** 欄位。
3.  貼上剛剛複製的 `AIza...` 金鑰。
4.  系統會自動儲存 (或點擊確認)。

---

## ✅ Step 3: 開始使用

現在，當你執行任務時，系統將優先使用你的專屬通道：

*   **影片分析**：支援長達數小時的影片與百萬字級的 Context。
*   **投影片生成**：圖片分析與版面配置的速度將顯著提升。
*   **隱私保障**：你的資料直接傳輸至 Google API，不經過第三方中轉。

---

## ❓ 常見問題 (FAQ)

### Q: 這會收費嗎？
**A: 不會**，除非你手動在 Google Cloud Console 綁定信用卡並開啟付費功能。預設的 Free Tier 是完全免費的，用完也只是暫時暫停，不會扣款。

### Q: Key 會過期嗎？
**A:** 通常不會，除非你手動刪除它。建議每半年檢查一次。

### Q: 使用我的 Key 安全嗎？
**A:** PrismFlow 採用 `BYOK` (Bring Your Own Key) 架構，金鑰僅在發送請求時使用，若是自架版 (Self-hosted) 則完全掌握在你手中。

---

*最後更新：2026-01-20 (v7.2.1)*
