---
description: 改版後自動測試並部署到 Google Cloud Run
---

# 部署流程 (自動化)

完成任何程式碼修改後，依照以下步驟執行：

## 1. 本地驗證
// turbo
```bash
cd /Users/bangdoll/Library/Mobile\ Documents/iCloud~md~obsidian/Documents/AI筆記/youtube_summary
python -m py_compile main.py slide_generator.py
```

## 2. 瀏覽器測試
使用 browser_subagent 開啟 https://youtube-summary-1031334287904.asia-east1.run.app/ 進行功能驗證：
- 確認頁面正常載入
- 測試修改的功能是否如預期運作
- 確認沒有 Console 錯誤

## 3. Git 提交
// turbo
```bash
cd /Users/bangdoll/Library/Mobile\ Documents/iCloud~md~obsidian/Documents/AI筆記/youtube_summary
git add -A
git commit -m "fix: [描述修改內容]"
```

## 4. 推送到 GitHub (觸發 Actions)
// turbo
```bash
cd /Users/bangdoll/Library/Mobile\ Documents/iCloud~md~obsidian/Documents/AI筆記/youtube_summary
git push origin main
```

## 5. 確認部署
通知用戶：已推送到 GitHub，Actions 正在部署中。約 2-3 分鐘後可刷新網頁測試。

---

// turbo-all
