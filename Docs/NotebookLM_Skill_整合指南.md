# NotebookLM Claude Skill 整合指南

本指南說明如何將 Google NotebookLM 的功能整合進 Claude Agent Workflow 中，讓 AI 能夠直接讀取、管理您的 NotebookLM 資料。

## 1. 環境準備與安裝

由於 `notebooklm-py` 套件要求 Python 3.10 以上版本，為避免干擾系統環境，我們採用 `uv` 工具進行隔離安裝。

### 安裝步驟

請在終端機執行以下指令：

```bash
# 1. 使用 uv 隔離安裝 notebooklm-py (包含瀏覽器自動化依賴)
uv tool install "notebooklm-py[browser]"

# 2. 安裝 Playwright 瀏覽器核心 (用於登錄流程)
uv run playwright install chromium
```

> **為什麼要用 `uv tool`？**
> `uv tool` 會為該工具建立一個獨立的虛擬環境 (Virtual Environment)，確保依賴套件不會與其他專案衝突，且能指定所需的 Python 版本。

---

## 2. 註冊為 Claude Skill

安裝完成後，需要將其註冊到 Claude 的 Skill 系統中，讓 Agent 能夠調用。

```bash
# 執行 Skill 安裝指令
# 注意：uv tool 預設安裝路徑在 ~/.local/bin
~/.local/bin/notebooklm skill install
```

成功後會顯示類似以下訊息：
> Installed NotebookLM skill to /User/xxx/.claude/skills/notebooklm/SKILL.md

---

## 3. 身份驗證 (關鍵步驟)

這是最重要的一步。首次使用需要手動進行網頁登錄以獲取憑證。

### 操作流程

1.  **開啟新的終端機分頁** (建議，以免干擾目前工作)。
2.  **執行登錄指令**：
    ```bash
    ~/.local/bin/notebooklm login
    ```
3.  **瀏覽器操作**：
    系統會自動彈出 Chrome/Chromium 視窗，請在視窗中登錄您的 Google 帳號。
4.  **保存憑證**：
    登錄成功並看到 NotebookLM 首頁後，**請務必回到終端機視窗，按下 `Enter` 鍵**。
    *如果不按 Enter，登錄 Session 將不會被保存。*

---

## 4. 驗證安裝

完成上述步驟後，您可以進行簡單測試。

### CLI 測試
在終端機輸入：
```bash
~/.local/bin/notebooklm list
```
如果成功，應會列出您目前帳號下的所有 Notebooks。

### Agent 測試
現在，您可以在與 Claude 的對話中直接下達指令，例如：

> "使用 NotebookLM skill 列出我的筆記本"
> "幫我讀取 '專案A' 筆記本的摘要"

---

## 5. 常見問題排除 (Troubleshooting)

*   **Q: 顯示 `zsh: command not found: notebooklm`**
    *   **A**: 這是因為 `~/.local/bin` 沒有在您的系統 PATH 環境變數中。
    *   **解法 1**: 使用完整路徑 `~/.local/bin/notebooklm`。
    *   **解法 2**:將路徑加入設定檔 (執行 `echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc` 並重啟終端)。

*   **Q: 登錄時瀏覽器閃退或報錯**
    *   **A**: 請確認已執行 `uv run playwright install chromium` 安裝必要的瀏覽器核心。

*   **Q: Agent 說找不到 Skill**
    *   **A**: 請確認 `notebooklm skill install` 執行成功，且檔案確實存在於 `~/.claude/skills/notebooklm/SKILL.md`。

*   **Q: 登錄時出現 `TargetClosedError` 或瀏覽器無法開啟**
    *   **A**: 這通常是因為舊的瀏覽器設定檔鎖定或是 Chrome 程序卡住。
    *   **解法**:
        1.  執行指令清除舊設定檔：`rm -rf ~/.notebooklm/browser_profile`
        2.  (選用) 強制清理卡住的 Chrome 程序：`pkill -f "Chrome"`
        3.  重新執行登錄：`~/.local/bin/notebooklm login`

*   **Q: 登錄憑證多久會過期？**
    *   **A**: 正常情況下憑證可維持**數週**。但若頻繁切換網路環境或 Google 安全機制被觸發，可能會導致 Session 提早失效。若 Agent 提示認證過期，只需重新執行一次 `login` 流程即可恢復。

---

## 6. 指令速查表 (Cheatsheet)

### CLI 命令
在終端機操作時使用：

*   **列出筆記本**: `notebooklm list --json`
*   **設置活動筆記本**: `notebooklm use <id>`
*   **創建新筆記本**: `notebooklm create "標題"`
*   **添加來源**: `notebooklm source add "URL"`
*   **提問**: `notebooklm ask "問題"`
*   **生成 Podcast**: `notebooklm generate audio`

### 自然語言命令 (Agent Skills)
在與 Claude 溝通時使用：

*   "Create a podcast about [主題]"
*   "Summarize these URLs"
*   "Generate a quiz from my research"
*   或者使用斜槓命令調用：`/notebooklm`
