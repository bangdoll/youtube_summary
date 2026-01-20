# Antigravity Agent Skills 完整教學指南

> 📚 本文檔詳細介紹如何使用 Antigravity 的 Skills 系統來擴展 AI Agent 的能力

---

## 🎯 什麼是 Skills？

Skills 是一套預定義的指令集，為 Antigravity Agent 提供特定領域的專業知識與工作流程。每個 Skill 都包含：

- **SKILL.md** - 核心指令文件（YAML 前置資料 + 詳細說明）
- **scripts/** - 輔助腳本（可選）
- **examples/** - 範例實作（可選）
- **resources/** - 額外資源（可選）

---

## 📁 目前可用的 Skills

| Skill 名稱 | 用途 |
|------------|------|
| `architecture` | 系統設計、API 設計、資料庫 schema |
| `code-review` | 程式碼審查、錯誤檢測、最佳實踐 |
| `code-explainer` | 用白話文解釋複雜程式碼給新手 |
| `debugging` | 系統化追蹤 bug、log 分析、根因分析 |
| `deployment` | Google Cloud Run 部署流程 |
| `documentation` | 自動生成 README、CHANGELOG、API 文檔 |
| `fastapi` | FastAPI 開發最佳實踐 |
| `frontend-review` | HTML/CSS/JavaScript 前端審查 |
| `git-workflow` | Git 工作流、commit 規範、PR 模板 |
| `pdf-processing` | NoteSlide 專案專用 PDF 處理 |
| `performance` | 效能瓶頸分析與優化 |
| `refactoring` | 識別 code smell、重構程式碼 |
| `security-audit` | OWASP 檢查、漏洞掃描 |
| `unit-testing` | 自動生成 pytest 單元測試 |

---

## 🛠️ 各 Skill 詳細介紹

### 1. 架構設計 (architecture)

**用途**：規劃可擴展、可維護的軟體架構

**核心原則**：
- 單一職責 - 每個元件只做一件事
- 關注點分離 - UI、業務邏輯、資料存取分開
- 依賴反轉 - 依賴抽象而非實作
- 開放封閉 - 對擴展開放，對修改封閉

**架構模式**：
```
┌─────────────────────────────────────┐
│         Presentation Layer          │  ← API / UI
├─────────────────────────────────────┤
│          Business Layer             │  ← 業務邏輯
├─────────────────────────────────────┤
│           Data Layer                │  ← 資料存取
├─────────────────────────────────────┤
│            Database                 │  ← 資料庫
└─────────────────────────────────────┘
```

**RESTful API 設計**：

| 方法 | 用途 | 範例 |
|------|------|------|
| GET | 讀取 | `GET /users/123` |
| POST | 建立 | `POST /users` |
| PUT | 完整更新 | `PUT /users/123` |
| PATCH | 部分更新 | `PATCH /users/123` |
| DELETE | 刪除 | `DELETE /users/123` |

---

### 2. 程式碼審查 (code-review)

**用途**：自動對 PR、diff 或程式碼片段進行全面審查

**審查清單**：

#### 正確性 (Correctness)
- [ ] 程式碼是否符合預期功能？
- [ ] 邏輯是否正確無誤？
- [ ] 是否有潛在的 null/undefined 問題？

#### 邊緣案例 (Edge Cases)
- [ ] 是否處理了空值、空陣列、空字串？
- [ ] 是否考慮了極端輸入值？
- [ ] 錯誤處理是否完善？

#### 效能 (Performance)
- [ ] 是否有不必要的迴圈或運算？
- [ ] 是否有潛在的記憶體洩漏？

#### 安全性 (Security)
- [ ] 是否有 SQL Injection 風險？
- [ ] 是否有 XSS 漏洞？
- [ ] 敏感資料是否妥善處理？

**回饋格式**：

```markdown
## 🔍 程式碼審查報告

### ✅ 優點
- [列出程式碼的優點]

### ⚠️ 建議改進
- [具體的改進建議，附上程式碼範例]

### 🐛 發現的問題
- [嚴重程度] 問題描述及修復建議

### 📊 總評
[整體評價與總結]
```

---

### 3. 程式碼解說 (code-explainer)

**用途**：將技術概念轉化為易懂的說明，適合教學與文檔

**解說原則**：
1. **由淺入深** - 從整體概念開始，再深入細節
2. **類比說明** - 用日常生活例子解釋技術概念
3. **視覺化** - 適時使用圖表、流程圖
4. **避免術語** - 必須用時要解釋

**程式概念類比庫**：

| 概念 | 類比 |
|------|------|
| **變數** | 標籤貼紙，可以貼在任何盒子上 |
| **函數** | 食譜，給原料產出成品 |
| **類別** | 餅乾模具，可以做出很多相似的餅乾 |
| **繼承** | 子女繼承父母的特徵，但有自己的特色 |
| **API** | 餐廳菜單，你點餐（請求）餐廳出菜（回應）|
| **資料庫** | 圖書館，有索引可以快速找到資料 |
| **快取** | 便利貼，把常用資訊寫在手邊 |
| **遞迴** | 俄羅斯娃娃，打開一個裡面還有一個 |

---

### 4. Debug 偵探 (debugging)

**用途**：使用結構化方法快速定位並解決問題

**系統化 Debug 流程**：

1. **問題定義**
   - 現象：發生了什麼？
   - 預期：應該發生什麼？
   - 重現步驟：如何重現？
   - 頻率：每次？偶發？特定條件？

2. **資訊收集**
   - 錯誤訊息完整內容
   - Stack trace
   - 相關 log
   - 環境資訊（OS、版本、依賴）

3. **假設與驗證**
   ```
   假設 → 設計實驗 → 驗證 → 縮小範圍 → 重複
   ```

**5 Whys 根因分析**：
```
問題：使用者無法登入
↓ Why?
伺服器返回 500 錯誤
↓ Why?
資料庫查詢失敗
↓ Why?
連線池耗盡
↓ Why?
連線未正確釋放
↓ Why?
例外處理缺少 finally 區塊 ← 根因
```

---

### 5. 部署工作流 (deployment)

**用途**：整合 Google Cloud Run 部署流程

**部署指令**：

```bash
# 1. 執行本地測試
uv run pytest tests/ -v

# 2. 建構 Docker 映像
docker build -t gcr.io/<PROJECT_ID>/<SERVICE_NAME>:latest .

# 3. 推送到 Container Registry
docker push gcr.io/<PROJECT_ID>/<SERVICE_NAME>:latest

# 4. 部署到 Cloud Run
gcloud run deploy <SERVICE_NAME> \
  --image gcr.io/<PROJECT_ID>/<SERVICE_NAME>:latest \
  --platform managed \
  --region asia-east1 \
  --allow-unauthenticated
```

**部署檢查清單**：

- [ ] `uv run pytest` 全部通過
- [ ] 靜態分析無錯誤 (`ruff check .`)
- [ ] 本地 Docker 測試正常
- [ ] 敏感資料使用環境變數
- [ ] 健康檢查端點 `/health` 返回 200
- [ ] 更新 CHANGELOG.md

---

### 6. 文檔生成 (documentation)

**用途**：自動生成專案文檔

**README.md 範本**：

```markdown
# 專案名稱

> 一行描述專案的核心價值

## ✨ 功能特色

- 🚀 功能一描述
- 📦 功能二描述

## 🚀 快速開始

### 安裝
\`\`\`bash
uv sync
\`\`\`

### 使用方式
\`\`\`bash
uv run python main.py
\`\`\`
```

**Docstring 規範 (Google Style)**：

```python
def function_name(param1: str, param2: int) -> bool:
    """函數簡短描述。

    Args:
        param1: 參數一的描述。
        param2: 參數二的描述。

    Returns:
        返回值的描述。

    Raises:
        ValueError: 當輸入無效時拋出。
    """
    pass
```

---

### 7. FastAPI 開發 (fastapi)

**用途**：FastAPI 開發最佳實踐

**專案結構**：
```
project/
├── main.py              # 應用程式入口
├── routers/             # API 路由
├── models/              # Pydantic 模型
├── services/            # 業務邏輯
├── database/            # 資料庫相關
└── utils/               # 工具函數
```

**Pydantic 模型設計**：

```python
from pydantic import BaseModel, Field

class ItemBase(BaseModel):
    """基礎模型"""
    name: str = Field(..., min_length=1, max_length=100)
    price: float = Field(..., gt=0)
    
class ItemCreate(ItemBase):
    """建立用（不含 id）"""
    pass

class ItemResponse(ItemBase):
    """回應用（含 id 與時間戳）"""
    id: int
    created_at: datetime
    
    model_config = {"from_attributes": True}
```

---

### 8. 前端審查 (frontend-review)

**用途**：HTML/CSS/JavaScript 前端程式碼審查

**HTML 最佳實踐**：
```html
<!-- ✅ 好：使用語意化標籤 -->
<header>
  <nav>...</nav>
</header>

<!-- 圖片必須有 alt -->
<img src="photo.jpg" alt="產品照片描述">

<!-- 表單必須有 label -->
<label for="email">Email</label>
<input type="email" id="email" name="email">
```

**CSS 命名規範 (BEM)**：
```css
/* Block__Element--Modifier */
.card { }
.card__title { }
.card__button--primary { }
```

**無障礙檢查 (a11y)**：
- [ ] 所有圖片有 alt 屬性
- [ ] 表單元素有 label
- [ ] 色彩對比度 > 4.5:1
- [ ] 可用鍵盤導航
- [ ] 焦點狀態可見

---

### 9. Git 工作流 (git-workflow)

**用途**：Git 工作流最佳實踐，確保團隊協作一致性

**Commit 訊息規範 (Conventional Commits)**：

| Type | 說明 | Emoji |
|------|------|-------|
| `feat` | 新功能 | ✨ |
| `fix` | 修復 bug | 🐛 |
| `docs` | 文檔更新 | 📚 |
| `style` | 格式調整 | 💄 |
| `refactor` | 重構 | ♻️ |
| `perf` | 效能優化 | ⚡ |
| `test` | 測試相關 | ✅ |
| `chore` | 雜項 | 🔧 |

**Commit 範例**：
```
feat(auth): 新增 Google OAuth 登入功能

- 整合 google-auth-oauthlib
- 新增 /auth/google 端點
- 支援 session 持久化

Closes #123
```

**Branch 命名規範**：

| 類型 | 格式 | 範例 |
|------|------|------|
| 功能 | `feature/<描述>` | `feature/user-auth` |
| 修復 | `fix/<issue-id>-<描述>` | `fix/123-login-error` |
| 熱修復 | `hotfix/<描述>` | `hotfix/security-patch` |
| 發布 | `release/<版本>` | `release/1.2.0` |

---

### 10. 效能優化 (performance)

**用途**：找出效能瓶頸、記憶體洩漏、查詢優化

**效能優化原則**：
1. **先測量，再優化** - 不要猜測瓶頸
2. **80/20 法則** - 20% 的程式碼佔 80% 的執行時間
3. **避免過早優化** - 先讓它能動，再讓它快

**常見效能問題**：

```python
# ❌ Bad: N+1 查詢
for user in users:
    print(user.orders)  # 每次都查資料庫

# ✅ Good: 預載入
users = User.query.options(joinedload(User.orders)).all()
```

```python
# ❌ Bad: 字串拼接
s = ""
for item in items:
    s += str(item)

# ✅ Good
s = "".join(str(item) for item in items)
```

---

### 11. 重構助手 (refactoring)

**用途**：識別 code smell、系統化重構程式碼

**Code Smell 識別清單**：

#### 膨脹類 (Bloaters)
- [ ] 過長函數 - 函數超過 20 行
- [ ] 過大類別 - 類別職責過多
- [ ] 過長參數列表 - 參數超過 3 個

#### 非必要項 (Dispensables)
- [ ] 重複程式碼
- [ ] 冗餘類別
- [ ] 死程式碼
- [ ] 過度設計

**重構技巧範例**：

```python
# Before
def process():
    if not data:
        raise ValueError("empty")
    if len(data) > 100:
        raise ValueError("too long")
    # 處理邏輯...

# After：提取函數
def validate(data):
    if not data:
        raise ValueError("empty")
    if len(data) > 100:
        raise ValueError("too long")

def process():
    validate(data)
    # 處理邏輯...
```

---

### 12. 安全審計 (security-audit)

**用途**：OWASP 檢查、漏洞掃描、安全最佳實踐

**OWASP Top 10 重點**：

#### SQL Injection
```python
# ❌ 危險
query = f"SELECT * FROM users WHERE id = {user_id}"

# ✅ 安全：參數化查詢
cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
```

#### XSS
```python
# ❌ 危險
return f"<div>{user_input}</div>"

# ✅ 安全
from markupsafe import escape
return f"<div>{escape(user_input)}</div>"
```

#### 敏感資料
```python
# ❌ 危險
API_KEY = "sk-1234567890"  # 硬編碼

# ✅ 安全
API_KEY = os.environ.get("API_KEY")
```

**安全檢測工具**：
```bash
# Python 安全掃描
pip install bandit
bandit -r ./src

# 依賴漏洞檢查
pip install safety
safety check

# JavaScript 依賴檢查
npm audit
```

---

### 13. 單元測試 (unit-testing)

**用途**：根據 pytest 規範自動生成單元測試

**測試結構**：

```python
# tests/test_<module_name>.py
import pytest

class TestClassName:
    """測試 ClassName 的所有方法"""
    
    def test_function_基本情況(self):
        """測試基本功能"""
        pass
    
    def test_function_邊緣案例(self):
        """測試邊緣情況"""
        pass
    
    def test_function_錯誤處理(self):
        """測試異常處理"""
        pass
```

**測試清單**：

1. **正向測試 (Happy Path)**
   - [ ] 標準輸入產生預期輸出
   
2. **邊緣案例 (Edge Cases)**
   - [ ] 空值 (None, [], {}, "")
   - [ ] 極值 (0, -1, maxint)
   
3. **錯誤處理 (Error Handling)**
   - [ ] 無效類型輸入
   - [ ] 預期的異常拋出

**執行指令**：
```bash
# 使用 uv 執行測試
uv run pytest tests/ -v

# 含覆蓋率報告
uv run pytest tests/ --cov=src --cov-report=html
```

---

## 🚀 如何使用 Skills

### 方法一：直接請求

在對話中直接說明你需要的功能：

```
請幫我審查這段程式碼
```

Agent 會自動載入 `code-review` Skill 並執行審查。

### 方法二：明確指定

指定使用特定 Skill：

```
使用 security-audit 技能檢查這個 API
```

### 方法三：組合使用

你可以在同一個工作流中使用多個 Skills：

```
1. 先用 code-review 審查程式碼
2. 再用 unit-testing 生成測試
3. 最後用 documentation 更新文檔
```

---

## 📝 自訂 Skills

你也可以建立自己的 Skill！

### Skill 文件結構

```yaml
---
name: my-custom-skill
description: 我的自訂技能描述
---

# 技能標題

## 使用說明
...

## 範例
...
```

### 存放位置

```
~/.gemini/antigravity/skills/
└── my-custom-skill/
    └── SKILL.md
```

---

## 🔗 相關資源

- Skills 存放位置：`~/.gemini/antigravity/skills/`
- 工作流位置：`.agent/workflows/`

---

> 💡 **提示**：Skills 會隨著 Antigravity 更新而擴充，定期檢查是否有新的 Skills 可用！
