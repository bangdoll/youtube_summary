# Antigravity Agent Skills 完整教學指南

> **一行摘要**：Agent Skills 讓 AI 助手自動學會專業技能，只需兩步就能安裝！

---

## 📖 什麼是 Agent Skills？

**Skills** 是擴充 Antigravity Agent 能力的開放標準。每個技能就是一個包含 `SKILL.md` 檔案的資料夾。

### 運作原理

```
對話開始
    ↓
Agent 掃描可用技能
    ↓
根據任務自動啟用相關技能
    ↓
遵循技能中的指令執行任務
```

Agent 會：
1. **掃描**：對話開始時掃描技能目錄
2. **匹配**：根據任務判斷要啟用哪個技能
3. **執行**：遵循 `SKILL.md` 中的詳細指令

---

## 🚀 快速安裝（兩步驟）

### 方法一：讓 AI 幫你裝

1. 把這個網址傳給 Antigravity：`antigravity.google/docs/skills`
2. 說：「讀完這些，幫我裝技能」

### 方法二：手動安裝

在技能目錄建立資料夾和 `SKILL.md` 檔案：

```bash
# 全域安裝（所有專案可用）
mkdir -p ~/.gemini/antigravity/skills/my-skill/

# 專案特定安裝
mkdir -p <專案根目錄>/.agent/skills/my-skill/
```

---

## 📁 技能結構

### 必要檔案：SKILL.md

```markdown
---
name: 技能名稱
description: 清楚描述技能用途（Agent 用這個判斷何時啟用）
---

# 技能詳細指令

[這裡寫具體的指令和規範...]
```

### 可選資源

```
my-skill/
├── SKILL.md          # 必要：主指令檔
├── scripts/          # 選用：輔助腳本
├── examples/         # 選用：參考實作
└── resources/        # 選用：範本與資產
```

---

## 📦 已安裝技能清單

### 基礎技能

| 技能 | 目錄名 | 功能 | 觸發情境 |
|------|--------|------|---------|
| 程式碼審查 | `code-review` | 審查 PR、找 bug、風格檢查 | 「審查這段 code」 |
| 單元測試 | `unit-testing` | pytest 自動生成測試 | 「幫這函數寫測試」 |
| 文檔生成 | `documentation` | README、CHANGELOG、docstring | 「更新 README」 |
| 部署工作流 | `deployment` | Cloud Run 部署流程 | `/deploy` |

### 開發輔助技能

| 技能 | 目錄名 | 功能 | 觸發情境 |
|------|--------|------|---------|
| 重構助手 | `refactoring` | 識別 code smell、提取函數 | 「重構這段程式碼」 |
| Git 工作流 | `git-workflow` | commit 規範、branch 策略 | 「commit message 怎寫」 |
| Debug 偵探 | `debugging` | 系統化追蹤 bug、log 分析 | 「幫我 debug」 |
| 效能優化 | `performance` | 找瓶頸、記憶體洩漏、查詢優化 | 「優化效能」 |

### 專案管理技能

| 技能 | 目錄名 | 功能 | 觸發情境 |
|------|--------|------|---------|
| 程式碼解說 | `code-explainer` | 用白話文解釋複雜程式碼 | 「解釋這段 code」 |
| 架構設計 | `architecture` | 系統設計、API 設計、DB schema | 「設計 API」 |
| 安全審計 | `security-audit` | OWASP 檢查、漏洞掃描 | 「檢查安全漏洞」 |

### 專案特化技能

| 技能 | 目錄名 | 功能 | 觸發情境 |
|------|--------|------|---------|
| FastAPI 開發 | `fastapi` | endpoint 設計、Pydantic 模型 | FastAPI 開發相關 |
| 前端審查 | `frontend-review` | HTML/CSS/JS 無障礙、效能 | 前端 code 相關 |
| PDF 處理 | `pdf-processing` | NoteSlide 專案專用 | PDF 處理相關 |

---

## 💡 最佳實踐

### 1. 保持單一職責
每個技能專注於解決**一項**特定任務。

```
✅ code-review     → 只做程式碼審查
✅ unit-testing    → 只做測試生成
❌ all-in-one      → 什麼都做（太雜）
```

### 2. 描述要清晰
描述是 Agent 判斷是否啟用技能的依據：

```yaml
# ✅ 好的描述
description: 根據 pytest 規範為 Python 程式碼自動生成單元測試

# ❌ 不好的描述
description: 測試相關
```

### 3. 包含決策樹
引導 Agent 在複雜情境下選擇正確路徑：

```markdown
## 何時使用此技能

- 使用者要求「寫測試」→ 啟用
- 使用者問「測試怎麼跑」→ 啟用
- 使用者只是問「pytest 是什麼」→ 不需啟用
```

### 4. 腳本當黑盒
提供 `--help` 讓 Agent 自己探索，不需要讀全部原始碼：

```markdown
## 可用腳本

執行 `scripts/generate.py --help` 查看所有選項
```

---

## 🔧 自訂技能範例

### 建立一個專案特定技能

```bash
# 1. 建立資料夾
mkdir -p .agent/skills/my-project-deploy/

# 2. 建立 SKILL.md
cat > .agent/skills/my-project-deploy/SKILL.md << 'EOF'
---
name: my-project-deploy
description: 我的專案專用部署流程，包含 staging 和 production 環境
---

# 部署流程

## Staging 環境
\`\`\`bash
./deploy.sh staging
\`\`\`

## Production 環境
\`\`\`bash
./deploy.sh production
\`\`\`

## 部署前檢查
- [ ] 所有測試通過
- [ ] 版本號已更新
- [ ] CHANGELOG 已更新
EOF
```

---

## 📍 技能存放位置

| 類型 | 路徑 | 適用場景 |
|------|------|---------|
| 全域 | `~/.gemini/antigravity/skills/` | 所有專案都可用 |
| 專案特定 | `<專案>/.agent/skills/` | 只有該專案可用 |

---

## ❓ 常見問題

### Q: 技能沒有被啟用怎麼辦？
檢查 `description` 是否足夠清晰，讓 Agent 能判斷何時使用。

### Q: 可以有多個技能同時啟用嗎？
可以！Agent 會根據任務複雜度啟用多個相關技能。

### Q: 如何更新技能？
直接編輯 `SKILL.md` 檔案，下次對話就會使用新版本。

### Q: 如何刪除技能？
刪除整個技能資料夾即可：
```bash
rm -rf ~/.gemini/antigravity/skills/skill-name/
```

---

## 📚 參考資源

- [官方文檔](https://antigravity.google/docs/skills)
- [Agent Skills 開放標準](https://agentskills.io/)

---

*最後更新：2026-01-17*
