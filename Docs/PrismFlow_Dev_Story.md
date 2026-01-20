# 從 NoteFlux 到 PrismFlow — 打造超越 NotebookLM 的簡報生成引擎

> **導讀**：這不是一篇傳統的技術文件，而是一段關於「執著」的開發旅程。我們如何從一個簡單的 Python 腳本，進化成一個能與 Google NotebookLM 互補的 AI 簡報系統？本文將揭露這 90 天開發過程中的技術轉折與架構思維。

---

## 🏗️ 第一章：為什麼要造輪子？
Google NotebookLM 無疑是 2025 年最強大的 AI 筆記工具。它能讀懂數百頁的論文，生成流暢的 Podcast (Audio Overview)。
但作為一個講求效率的知識工作者，我在使用中遇到了一個巨大的斷層：

> 「Podcast 很好聽，但我明天開會要用的是 **PowerPoint**。」

NotebookLM 給了我知識的「聲音」，卻沒給我知識的「載體」。我需要一個工具，能接手 NotebookLM 吐出的 PDF 筆記，將其轉化為**真正可編輯** (Editable)、**版面乾淨** (Clean Layout) 的 **.pptx** 檔案。

這就是 **PrismFlow (原名 NoteFlux)** 的起點。

---

## 🧪 第二章：暴力美學 (The OCR Era)
### 初期嘗試：讓 AI「看」PDF
最早的版本 (NoteFlux v1.0) 思路非常直觀：
1. 把 PDF 轉成圖片。
2. 丟給 **Gemini Vision** 模型。
3. 叫 AI 告訴我標題在哪、內文在哪。

這聽起來很美好，但現實很骨感。Gemini 雖然看得很懂圖片內容，但它對「像素座標 (Bounding Box)」的掌握度極差。AI 回傳的座標經常飄移，導致生成的投影片文字忽上忽下，像喝醉了一樣。

### 妥協的藝術：Split Layout
為了解決這個問題，我在 **v2.8** 做了一個大膽的妥協——放棄精確定位。
我們採用了 **Split Layout (左圖右文)** 的設計：
- **左邊 50%**：直接放上 PDF 原圖（甚至保留了上面的文字）。
- **右邊 50%**：放上 AI 整理後的重點。

這雖然解決了資訊遺漏的問題，但「醜」是原罪。這看起來不像一份專業簡報，更像是一份閱讀測驗試卷。我們需要更進一步。

---

## 🎨 第三章：像素與向量的戰爭 (Native Vector Stripping)
### 在破壞中重建
使用者的核心訴求是：「保留原本漂亮的背景圖表，但是把文字換成我想要的。」
這意味著我們需要一張 **Clean Plate** (乾淨底圖)。

在 **v3.0** 以前，我試圖用 AI Inpainting (修圖) 來「塗掉」文字。
然而，AI 修圖有兩個致命傷：
1. **慢**：每張圖要修 3-5 秒。
2. **偽影**：遇到複雜漸層背景，AI 容易塗出一塊塊灰色的補丁 (Gray Artifacts)。

### 技術轉折點：v4.0 架構
在 **v4.0**，我們迎來了最大的架構變革——**Native Vector Stripping (原生向量剝離)**。
我們不再把 PDF 當作一張死圖，而是把它看作層疊的物件。透過 **PyMuPDF** 函式庫，我們學會了各種「外科手術」：

```python
# 概念代碼：如何「隱藏」PDF 中的文字層，只保留背景
doc = fitz.open("source.pdf")
for page in doc:
    # 告訴渲染器：不要畫出文字 (Text Operations = 3)
    # 我們不是刪除文字，而是讓它「隱形」
    pix = page.get_pixmap(flags=fitz.pdfcolor['non-text'])
    pix.save("clean_background.png")
```

這個改變是巨大的。我們瞬間獲得了 **100% 完美的背景圖**，原本的向量圖表、公司 Logo、細緻的漸層與線條都被完整保留，而文字消失得無影無蹤。

這就是 PrismFlow 的核心魔術：**向量級的減法，像素級的還原**。

---

## ☁️ 第四章：與雲端極限博弈 (The 413 Error)
### 伺服器的怒吼
隨著功能與畫質提升，我們撞上了 Google Cloud Run 的硬體限制。
當使用者上傳一份 30 頁的高畫質 PDF，前端試圖將解析完的結果（包含 30 張 1600px 的 Base64 圖片）傳回後端生成 PPTX 時，伺服器直接拒絕了請求。

**`413 Request Entity Too Large`**

Google Cloud Run 的 HTTP 請求上限是 **32MB**。而我們的 JSON Payload 經常高達 50MB 甚至 100MB。

### 第一次嘗試：壓縮 (Client-Side Compression)
在 **v6.3**，我試圖在前端進行極限壓縮：
- 將圖片縮小至 1024px。
- JPEG 品質降至 0.5。
這雖然勉強讓 payload 降到了 25MB，但代價是畫質的肉眼可見劣化。這不是長久之計。

### 終極解法：Session Management (v7.0)
我們反思了一個問題：**「為什麼我們要讓圖片在網路來回傳輸？」**

流程原本是：
`後端生成圖片` -> `傳給前端預覽` -> `前端傳回後端生成 PPT` (Payload 爆炸💥)

我們重構了整個後端架構，引入了 **Session State**：
1. 後端分析完成後，將圖片物件直接暫存在伺服器的記憶體中 (`slide_sessions`)，並只給前端一個 `session_id`。
2. 前端預覽使用的是輕量化的縮圖 URL。
3. 最後生成時，前端只需要回傳 `{ "session_id": "xyz-123", "text_edits": [...] }`。

**成效驚人**：
- Payload 大小：從 **50MB** 暴跌至 **50KB**。
- 傳輸速度：從 10 秒降至 **0.1 秒**。
- 畫質：因為後端使用的是記憶體中的原始圖檔，生成的 PPTX 畫質回到了 100% 無損。

這一役，讓我們學會了如何在 Stateless 的雲端環境中，優雅地管理 State。

---

## 🤝 第五章：賦予人類控制權 (Human-in-the-Loop)
### Web Editor 的誕生
AI 再強大，依然會有幻覺。它可能會把重要的財務數據「摘要」掉，或是把標題理解錯誤。
如果使用者只能拿到最後的 PPTX 才能修改，那體驗太差了。

在 **PrismFlow v2.10**，我們推出了 **Web Slide Editor**。
這是一個 **所見即所得 (WYSIWYG)** 的編輯器。

- **AI 是副駕駛**：它幫你把背景清乾淨，把草稿填好。
- **你是機長**：你在網頁上直接看著最後的合成效果。
    - 這裡的字太小？點一下放大。
    - AI 漏了一段話？直接在網頁上補進去。
    - 想要改標題顏色？即時調色盤。

當你按下「生成 PPTX」那一刻，你心裡是踏實的，因為你已經看過結果了。這才是 AI 工具該有的互動模式——**增強人類，而非取代人類**。

---

## 🔭 結語及展望
PrismFlow 的開發過程，是一場 **Vibe Coding** 的實踐。我們沒有預先寫好幾百頁的規格書，而是追隨使用者的真實痛點，在技術的邊界上即興創作。

從最初簡陋的 OCR 腳本，到現在擁有 Session 架構、Native PDF 處理與 Web Editor 的成熟產品，PrismFlow 證明了一件事：
**好的 AI 產品，不在於模型有多大，而在於它如何精準地嵌入使用者的工作流。**

### 技術棧一覽 (Stack)
- **Frontend**: Vanilla JS (No Frameworks), CSS Variables, SSE (Server-Sent Events)
- **Backend**: Python, FastAPI, Uvicorn
- **Core Libraries**:
    - `pymupdf`: 向量剝離與文字提取
    - `python-pptx`: 簡報生成引擎
    - `google-genai`: Gemini 3 Flash/Pro 模型串接
- **Infrastructure**: Google Cloud Run, Docker

---
*本文由 PrismFlow 開發者 [蔡正信-數位教練] 撰寫，紀錄於 2026/01/18*
