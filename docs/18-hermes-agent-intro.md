# 第十八章：Hermes Agent 入門

> 狀態：撰寫中。18-1 依官方文件整理；18-2 之後的實測結果待 Hermes CLI 安裝完成後補上。依使用者指示，本機**不安裝 Hermes Desktop**，桌面版專屬畫面以 CLI 等價做法取代並標註。

## 18-1 Hermes Agent 是什麼

### 18-1-1 會累積技能的 Agent

Hermes Agent 是 Nous Research 開源（MIT）的 AI agent，官方自稱「The self-improving AI agent」：它在完成多步驟任務後會把可重複的流程寫成 **skill**（`~/.hermes/skills/<name>/SKILL.md`），下次遇到類似任務時自動載入，並在使用中持續修改。有一個背景的 **Curator** 定期整理這些技能（14 天沒用標成 stale、30 天歸檔，可選擇用 LLM 合併重複的技能）。這是它和 Claude Code、Codex CLI 之類 coding agent 最大的差異：後者的技能是人寫的，Hermes 的技能主要是它自己寫的。

其他主要能力：終端機與檔案工具、網頁搜尋、六種終端機後端（local / Docker / SSH / Modal / Daytona / Vercel Sandbox）、排程（cron）、子 Agent（`delegate_task`）、MCP、持久記憶（`MEMORY.md` / `USER.md`）、訊息平台 gateway（Telegram、Discord、Slack、LINE 等近 30 個）。

### 18-1-2 Hermes Agent 與 Hermes 模型

兩個是不同的東西，只是同一家公司取了同一個名字：

| | Hermes 模型 | Hermes Agent |
|---|---|---|
| 是什麼 | Nous Research 微調的開放權重 LLM（Hermes 3、Hermes 4 系列） | 執行工具、管理記憶與技能的 agent 程式（harness） |
| 跟模型的關係 | 它本身就是模型 | **模型無關**（官方：「Use any model you want」），用 `hermes model` 切換 |
| 可接的來源 | — | Nous Portal（300+ 模型）、OpenRouter、OpenAI、Anthropic、本機 OpenAI 相容端點（Ollama、llama-server、LM Studio）等 |

本章用的是 Hermes Agent 接本機 Ollama 的 Qwen 模型，完全不用 Hermes 模型。

### 18-1-3 與 OpenClaw、OpenShell 的關係

- **OpenClaw**：另一個開源個人 agent（原名 Clawdbot / Moltbot）。Hermes 可以匯入它的設定、記憶、技能與 API key：`hermes import-agent openclaw`（舊寫法 `hermes claw migrate`），同一個指令也能匯入 Claude Code、Codex CLI、Cursor 的設定。Ollama 的 `ollama launch` 也同時支援 `hermes` 和 `openclaw`。
- **OpenShell**：NVIDIA 開源的 agent 沙箱執行環境：用政策宣告 agent 能碰什麼網路和檔案，核心層強制執行，真實憑證不進沙箱。官方支援 Linux、**macOS Apple Silicon**、Windows WSL2（實驗性），需要 Docker / Podman 或主機虛擬化。NVIDIA 的 **NemoClaw** 是在 OpenShell 裡一鍵部署 agent 的工具，預設 agent 是 OpenClaw，`nemohermes` 則是預選 Hermes 的別名；Hermes 的設定會放在沙箱內的 `/sandbox/.hermes`，推論可以路由到本機 Ollama。第十九章 19-6-3 討論。

## 18-2 安裝桌面版

### 18-2-1 桌面版與 install.ps1

**本機略過（Windows）。** `install.ps1` 是 Windows PowerShell 的安裝腳本。macOS 的對應指令是：

```sh
curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash
```

官方文件明確列出 **Homebrew 安裝（`brew install hermes-agent`）是不支援的方式**，雖然 formula 存在（0.22.4）。本機採官方腳本。腳本做的事（讀過原始碼確認）：下載固定版本的 `uv`，用它裝 Python 3.14 與 Hermes 原始碼到 `~/.hermes/hermes-agent/`，啟動器放 `~/.local/bin/hermes`，並在 `~/.zshrc` 加一行把 `~/.local/bin` 加進 PATH。預設還會裝 Chromium（瀏覽器工具）和 `cua-driver`（電腦操作），可用 `--skip-browser --skip-computer-use` 略過。

### 18-2-2 從 Microsoft Store 安裝

**本機略過（Windows）。** macOS 的桌面版是 DMG（Apple Silicon only），或 `brew install --cask hermes-desktop`。本機依指示不安裝桌面版。

### 18-2-3 開啟桌面版

**本機略過：未安裝桌面版。** 桌面版與 CLI 共用 `~/.hermes` 下的所有設定、sessions、技能、記憶；若日後安裝，`hermes desktop` 也能從 CLI 啟動它。

（以下各節待驗證後補上）
