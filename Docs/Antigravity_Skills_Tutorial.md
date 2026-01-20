# Antigravity Skills 完整教學指南

> 擴展你的 AI 助手能力的秘密武器

---

## 什麼是 Skills？

**Skills** 是一套指令、腳本和資源的集合，用來擴展 Antigravity 的專業能力。每個 Skill 都是針對特定任務的「深度專業知識」。

### Skill 的本質

```
Skills = 專業知識 + 標準流程 + 最佳實踐
```

當你問 Antigravity「幫我審查這段程式碼」時，它不只是隨便看看——而是會載入 **code-review** Skill，按照完整的審查清單逐項檢查。

---

## Skill 的結構

每個 Skill 都存放在一個獨立資料夾中：

```
~/.gemini/antigravity/skills/
├── code-review/
│   └── SKILL.md        # 主要指令檔（必要）
├── debugging/
│   └── SKILL.md
├── performance/
│   ├── SKILL.md
│   └── scripts/        # 輔助腳本（可選）
└── ...
```

### SKILL.md 格式

```markdown
---
name: skill-name
description: 技能的簡短描述，說明它能做什麼
---

# 技能標題

[詳細的指令、清單、範例程式碼等]
```

**三個關鍵部分**：
1. **YAML 前置資料** — `name` 和 `description`
2. **使用情境說明** — 何時、如何使用
3. **具體指令與範例** — 檢查清單、程式碼模板、回報格式

---

## 目前可用的 Skills

| Skill | 描述 | 使用時機 |
|-------|------|----------|
| `architecture` | 系統設計、API 設計、資料庫 schema | 規劃新專案或重構現有架構 |
| `code-explainer` | 程式碼解釋 | 理解他人或舊程式碼 |
| `code-review` | 程式碼審查 | PR 審查、找 bug、改進建議 |
| `debugging` | 系統化 debug | 追蹤 bug、分析 log、根因分析 |
| `deployment` | 部署相關 | CI/CD、Docker、雲端部署 |
| `documentation` | 文件撰寫 | 寫 README、API 文件 |
| `fastapi` | FastAPI 開發 | Python API 開發 |
| `frontend-review` | 前端審查 | HTML/CSS/JS 最佳實踐、a11y |
| `git-workflow` | Git 工作流程 | 版本控制、分支策略 |
| `pdf-processing` | PDF 處理 | 提取、轉換 PDF 內容 |
| `performance` | 效能優化 | 找瓶頸、記憶體優化 |
| `refactoring` | 程式碼重構 | 改善程式碼結構 |
| `security-audit` | 安全審計 | 找漏洞、安全檢查 |
| `unit-testing` | 單元測試 | 生成 pytest 測試 |

---

## 如何使用 Skills

### 自動觸發

當你的請求與某個 Skill 相關時，Antigravity 會自動識別並載入。例如：

- 「幫我審查這段程式碼」→ 載入 `code-review`
- 「這個 bug 怎麼追」→ 載入 `debugging`
- 「幫我寫測試」→ 載入 `unit-testing`

### 手動觸發

如果想確保使用特定 Skill，可以在請求中明確提及：

```
用 code-review skill 幫我審查 main.py
```

---

## 實際範例

### 範例 1：程式碼審查

**你說**：「幫我審查這個函數」

**Antigravity 會使用 code-review Skill，檢查**：
- ✅ 正確性 — 邏輯是否正確
- ✅ 邊緣案例 — 空值、極端輸入
- ✅ 程式碼風格 — 命名、規範
- ✅ 效能 — 不必要的迴圈
- ✅ 安全性 — SQL Injection、XSS

**輸出格式**：
```markdown
## 🔍 程式碼審查報告

### ✅ 優點
- 函數命名清晰
- 錯誤處理完整

### ⚠️ 建議改進
- 第 15 行可用 list comprehension 簡化

### 🐛 發現的問題
- [中] 未處理空陣列輸入

### 📊 總評
整體良好，建議加強邊緣案例處理
```

---

### 範例 2：Debug 追蹤

**你說**：「用戶登入突然壞掉了，幫我追」

**Antigravity 會使用 debugging Skill，執行**：

1. **問題定義** — 現象、預期、重現步驟
2. **資訊收集** — 錯誤訊息、log、環境
3. **5 Whys 分析** — 找到根本原因
4. **解決方案** — 程式碼修改 + 預防措施

---

### 範例 3：效能優化

**你說**：「這個函數跑太慢，幫我看看」

**Antigravity 會使用 performance Skill**：

1. **測量**而非猜測 — 用 cProfile 找瓶頸
2. **識別常見問題** — N+1 查詢、字串拼接、重複計算
3. **提供優化建議** — 具體程式碼改進
4. **輸出效能報告** — Before/After 數據對比

---

## 如何建立自己的 Skill

### Step 1：建立資料夾

```bash
mkdir -p ~/.gemini/antigravity/skills/my-custom-skill
```

### Step 2：建立 SKILL.md

```markdown
---
name: my-custom-skill
description: 我的自訂技能，用於 OOO 場景
---

# 我的自訂技能

## 使用時機
當使用者要求 XXX 時...

## 檢查清單
- [ ] 第一項
- [ ] 第二項

## 輸出格式
[定義標準化的輸出格式]
```

### Step 3：可選的進階結構

```
my-custom-skill/
├── SKILL.md          # 主要指令（必要）
├── scripts/          # 輔助腳本
│   └── helper.py
├── examples/         # 範例檔案
│   └── sample.json
└── resources/        # 資源檔案
    └── template.md
```

---

## 最佳實踐

### 1. 具體勝過模糊

```markdown
# ❌ 不好
檢查程式碼品質

# ✅ 好
- [ ] 所有函數都有 docstring
- [ ] 變數命名符合 snake_case
- [ ] 沒有超過 20 行的函數
```

### 2. 提供輸出模板

讓 AI 的回覆有一致的格式，方便閱讀和比較。

### 3. 附上程式碼範例

```markdown
# ❌ 不好
使用現代寫法

# ✅ 好
```python
# 舊寫法
for item in items:
    result.append(item.name)

# 現代寫法
result = [item.name for item in items]
```
```

### 4. 建立檢查清單

清單比長篇大論更有效，也更容易追蹤執行狀態。

---

## 總結

| 概念 | 說明 |
|------|------|
| **Skill 是什麼** | 擴展 AI 專業能力的知識包 |
| **存放位置** | `~/.gemini/antigravity/skills/` |
| **必要檔案** | `SKILL.md` |
| **格式** | YAML 前置資料 + Markdown 內容 |
| **觸發方式** | 自動識別 或 手動指定 |

---

> **Pro Tip**: Skill 的威力在於「標準化」。當你有了固定的審查清單、debug 流程、測試模板，AI 的輸出品質會大幅提升，而且每次都是一致的水準。
