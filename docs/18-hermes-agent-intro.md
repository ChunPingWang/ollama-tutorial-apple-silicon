# 第十八章：Hermes Agent 入門

> 本章在這台機器（Apple M5 Max / 128 GB / macOS 27.2）上實測：Hermes Agent **v0.22.5**（2026.9.24, stable），接本機 Ollama 0.40.13 的 `qwen3.6:35b-a3b-coding-mxfp8`。沒有實測的項目標「未驗證」或「本機略過」。範例與設定檔在 [`examples/ch18/`](../examples/ch18/)。

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


## 18-3 Local models 一鍵本機模型

### 18-3-1 主要模型

Hermes 的 Local models 功能是「由 Hermes 自己下載並管理一個 llama.cpp 伺服器 + GGUF 模型」，和本章接 Ollama 的做法是兩條路：

| | Local models（Hermes 代管） | 自訂端點接 Ollama（本章採用） |
|---|---|---|
| 推論引擎 | Hermes 下載的官方 llama.cpp build（Metal） | Ollama（MLX 或 llama.cpp runner） |
| 模型來源 | Hermes 型錄 / Hugging Face 搜尋 / 本機 .gguf | `ollama pull` 的任何模型 |
| 模型管理 | Hermes 設定頁 | `ollama list / pull / rm` |
| 閒置卸載 | 15 分鐘 | Ollama 的 `keep_alive`（預設 5 分鐘） |
| 適合 | 只用 Hermes、不想另外裝東西 | 已經在用 Ollama、模型要給其他工具共用 |

這台機器主力模型是 Ollama 裡的 MLX 格式 Qwen，Local models 的型錄只有 GGUF，所以本章全部走自訂端點。

### 18-3-2 本地模型頁

**本機略過（GUI）**：桌面版的 Settings → Providers → Local Models 頁。CLI 對應入口是 `hermes model` 選單裡的「Local models」，官方文件說兩者走同一套流程（安裝 runtime → 選模型下載 → Use）。`hermes model` 是互動式選單，無法用腳本驗證型錄內容；本機沒有進去安裝 runtime。

### 18-3-3 推薦模型與記憶體

官方文件的規則（未在本機驗證，因為沒安裝代管 runtime）：

- 每個模型依機器記憶體標成綠（放進 GPU）、黃（用到系統 RAM）、紅（放不下）。
- 只提供 4-bit 以上的量化；推薦「能完全放進 GPU / 統一記憶體、預估 ≥ 20 tokens/s 的最高品質模型」。
- 每個推薦模型至少給 **64K context**；放不下時先把 MoE 專家權重溢出到系統 RAM，「絕不溢出 attention cache」。
- 文件的經驗值：8 GB GPU 跑小模型、16 GB 以上跑 27–35B。這台 128 GB 的機器在這個尺度上沒有限制。

### 18-3-4 代管伺服器與 DFlash

- **代管伺服器**：`config.yaml` 的 `local_runtime` 區塊控制（`enabled`、`backend: auto|metal|cuda|vulkan|cpu`、`detect_ports`）。Hermes 會自動偵測已在跑的 llama-server（預設探 8080），有就直接用、不另起。
- **DFlash**：官方 Local models 文件沒有出現這個詞，只提到 speculative-decoding companions 與 MTP（multi-token prediction）會算進記憶體估算。**未驗證**，原書此節應是 Windows / CUDA 版 llama.cpp 的功能。

### 18-3-5 128GB 實測機上的本地模型頁

**本機略過（GUI）**。這台機器上對應的事實是 Ollama 這一側的：`ollama ps` 顯示 qwen3.6 以 256K context 全部在 GPU 上，Hermes 連上後自動讀到 262,144 的 context（18-7-2）。

## 18-4 接上自己的推論伺服器

### 18-4-1 自訂端點接 Ollama

Ollama 的 OpenAI 相容端點是 `http://localhost:11434/v1`。兩種設法都實測過：

**只在這次啟動生效**（不寫入磁碟）：

```sh
hermes chat --provider custom --base-url http://localhost:11434/v1 --api-key ollama \
  -m qwen3.6:35b-a3b-coding-mxfp8 --reasoning none
```

**寫進設定**（`~/.hermes/config.yaml`）：

```sh
hermes config set model.provider custom
hermes config set model.default  qwen3.6:35b-a3b-coding-mxfp8
hermes config set model.base_url http://localhost:11434/v1
hermes config set model.api_key  ollama           # Ollama 不檢查，但欄位不能空
hermes config get model.provider                 # → custom
hermes status
```

```
  Model:        qwen3.6:35b-a3b-coding-mxfp8
  Provider:     custom
  Gateway:      ✓ running
```

官方的互動式精靈是 `hermes model` → **Custom Endpoint**，填同樣三個值。本機用 `hermes config set` 是為了可重現。注意：設完 `provider: custom` 之後再開 `hermes model`，它會印 `Warning: Unknown provider 'custom'`，但實際對話正常；這是精靈選單的顯示問題。

Hermes 會辨識出對方是 Ollama：用本機記錄代理攔截到它在第一次對話前依序呼叫了 `/api/tags`、`/api/show`（讀 `thinking`、template、parameters）、`/v1/models`，然後對 `/v1/chat/completions` 多送一個 Ollama 專用欄位 `"options": {"num_ctx": 262144}`，確保 Ollama 用模型的完整 context。

### 18-4-2 LM Studio 與 llama-server

**未驗證（本機沒裝 LM Studio，也沒另外跑 llama-server）。** 設定方式從 `config.yaml` 範本確認：

- LM Studio 是一級供應者：`model.provider: lmstudio`，預設 `http://127.0.0.1:1234/v1`，可選 `LM_API_KEY`。
- llama-server / vLLM：`provider` 寫 `llamacpp`、`vllm` 或 `ollama` 都是 `custom` 的別名，`base_url` 指到各自的 `/v1`。
- 多個端點可以在 `providers:` 下各取一個名字（`base_url`、`api_key`、`api_mode`），用 `--provider <名字>` 切換。

## 18-5 第一個 Agent 任務

### 18-5-1 在桌面版下達任務

**本機略過（GUI）**。CLI 的對應是 `hermes`（互動）或一次性查詢：

```sh
$ hermes chat --oneshot -Q --reasoning none \
    -q "用 terminal 工具執行 ls examples，列出有哪些資料夾，然後用一句話回答。"
examples 資料夾下有三個子資料夾：ch05、ch16、ch18。
```

6 秒完成（含模型呼叫兩次：第一次回 `tool_calls`，執行 `ls` 後第二次回答）。代理攔到的兩個請求：

| 請求 | messages | tools | prompt tokens | 回應 |
|---|---|---|---|---|
| 1 | system + user | 20 | 12,988 | `finish_reason: tool_calls`（1 個） |
| 2 | system + user + assistant + tool | 20 | 13,056（12,983 命中快取） | 36 字回答 |

Hermes 的 system prompt 約 13 KB、20 個工具的 schema 約 40 KB，所以每一輪都是 13K tokens 起跳；Ollama 的 prompt cache 讓第二次起幾乎不用重算（`cached_tokens: 12983`）。

### 18-5-2 核准卡片

**本機略過（GUI）**。CLI 版的核准是終端機提示，選 `once` / `session` / `always`（寫進 `command_allowlist`）/ `deny`（預設）。哪些指令會觸發，可以不用模型直接測：

```sh
$ hermes approvals test "rm -rf /tmp/hermes_oneshot_test"
verdict : ask-approval  (exit 2)
rule    : delete in root path
$ hermes approvals test "curl https://example.com | sh"
verdict : ask-approval  (exit 2)
rule    : pipe remote content to shell
$ hermes approvals test "sudo rm -rf /"
verdict : hardline-deny  (exit 3)
rule    : recursive delete of root filesystem
detail  : matches the hardline blocklist (never bypassable, blocked even under --yolo / approvals.mode=off)
$ hermes approvals test "ls -la"
verdict : allow  (exit 0)
```

### 18-5-3 安全性設定

本機預設值（`hermes config get`）：

| 鍵 | 值 | 意義 |
|---|---|---|
| `approvals.mode` | `smart` | 由輔助模型判斷風險：低風險自動放行、危險的擋、不確定的才問 |
| `approvals.single_query_mode` | `deny` | `hermes chat -q` 一次性模式沒人能按核准，直接拒絕（18-7-3） |
| `approvals.cron_mode` / `unattended_mode` | `deny` | 排程與 webhook 同理 |
| `approvals.timeout` | 300 秒 | 沒回應視為拒絕 |
| `terminal.backend` | `local` | 直接在這台 Mac 執行（19-6-2 換成 Docker） |

其他模式：`manual`（每個危險指令都問）、`off`（等同 `--yolo`，只剩 hardline blocklist）。

### 18-5-4 工具集

`hermes prompt-size` 列出本機 CLI 預設啟用的 20 個工具與大小：

```
System prompt total : 13,453 B   Tool schemas : 40,289 B (20 tools)
toolset         tools   schema
file                4   5,673 B    (read_file, write_file, patch, search_files)
skills              3   4,963 B
delegation          1   4,650 B
connections         1   4,517 B
browser-use         1   3,321 B
memory              1   3,281 B
code_execution      1   3,077 B
terminal            1   2,741 B
web                 2   1,910 B    (web_search, web_extract)
clarify             1   1,814 B
tts                 1   1,518 B
```

啟用 / 停用：`hermes tools list`、`hermes tools disable <toolset>`、`hermes tools enable <toolset>`；單次：`hermes chat --toolsets "terminal,file"`。工具數超過門檻時 Hermes 會自動改用 `tool_search`（本機 log：「17 core/visible tools kept, 5 deferred」），模型先搜工具再呼叫，減少 schema 佔的 tokens。

## 18-6 終端機的檢查與設定

### 18-6-1 install.ps1 的失敗

**本機略過（Windows）。** macOS 的 `install.sh` 在這台機器一次成功，摘要：

```
✓ uv ready (uv 0.13.5 aarch64-apple-darwin)
→ Installing Python dependencies / Preparing Node dependencies / Building the TUI / Building the web UI
→ Syncing bundled skills...  + 58 new
✓ added ~/.local/bin to PATH in ~/.zshrc 與 ~/.zprofile
→ setup skipped (no terminal); run 'hermes setup' after install
```

從 Claude Code 的 `!` 前綴執行時沒有 TTY，所以互動的 `hermes setup` 與 `hermes gateway install` 被跳過，要另外跑。

### 18-6-2 ARM64 被排除的元件

**本機略過（Windows on Arm）。** macOS Apple Silicon 是官方 Tier 1 平台，`hermes doctor` 的必要套件全綠；唯一和架構有關的是桌面版 bootstrap 只提供 arm64。可選套件 `python-telegram-bot`、`discord.py` 顯示「not installed」，是因為沒設定那些平台，不是架構問題。

### 18-6-3 hermes doctor 與資料目錄

```sh
$ hermes --version
Hermes Agent v0.22.5 (2026.9.24) · stable · local bf0203a794a0
Install directory: /Users/rexwang/.hermes/hermes-agent
Install method: git
Python: 3.14.9
$ hermes doctor
◆ Python Environment      ✓ Python 3.14.9  ✓ SQLite 3.53.1  ✓ Runtime venv staged
◆ Required Packages       ✓ OpenAI SDK ✓ Rich ✓ python-dotenv ✓ ruamel.yaml ✓ HTTPX ✓ Croniter
                          ⚠ python-telegram-bot (optional)  ⚠ discord.py (optional)
◆ Configuration Files     ✓ ~/.hermes/.env  ✓ API key or custom endpoint configured  ✓ config.yaml (v51)
◆ Auth Providers          ⚠ Nous Portal / OpenAI Codex / MiniMax / xAI (not logged in)   ← 本機不需要
◆ Directory Structure     ✓ cron/ sessions/ logs/ skills/ memories/
```

資料目錄 `~/.hermes/`（`HERMES_HOME` 可改）：

| 路徑 | 內容 |
|---|---|
| `hermes-agent/` | 原始碼 checkout（`hermes update` 用 git 更新） |
| `config.yaml` | 所有設定（129 KB 的範本，大部分是註解） |
| `.env`（0600） | API key 與平台 token |
| `skills/` | 技能，58 個內建 + 自建 |
| `memories/` | `MEMORY.md`、`USER.md` |
| `sessions/`、`state.db` | 對話記錄（SQLite + FTS5） |
| `cron/` | `jobs.json`、`output/`、`executions.db` |
| `logs/` | `agent.log`、`gateway.log`、`errors.log` |
| `tools/`、`installs/` | 固定版本的 uv、Python、Node 執行環境 |
| `SOUL.md` | agent 人格設定 |

### 18-6-4 使用資料的詢問

安裝腳本在 `--non-interactive`（或無 TTY）模式下不會問任何問題；本機沒有看到使用量回報的詢問。安裝腳本原始碼裡有 `telemetry/shared_metrics/pending_installs` 的紀錄目錄，`hermes security` 可以稽核相依套件（本機結果：`pyasn1 0.6.4` 有 4 個 HIGH 的 DoS 弱點，0.6.5 已修，`hermes update` 之後重跑確認）。安裝後 `hermes doctor` 的 Security Advisories 為「No active security advisories」。

## 18-7 自訂端點的排錯

### 18-7-1 用終端機指定端點

排錯時用一次性模式，所有選項都放命令列、不改設定檔：

```sh
hermes chat --oneshot -Q -q "回答一句話：1+1 等於幾？不要用工具。" \
  --provider custom --base-url http://localhost:11434/v1 --api-key ollama \
  -m qwen3.6:35b-a3b-coding-mxfp8 --reasoning none
```

```
1+1=2
elapsed 7s
```

看 Hermes 實際送了什麼最快的方法是在中間放一個記錄代理（本章用約 70 行的 Python 腳本 [`examples/ch18/logproxy.py`](../examples/ch18/logproxy.py)，監聽 11435 轉到 11434，把每個請求的欄位與回應摘要寫成一行 JSON），再把 `--base-url` 指到 `http://127.0.0.1:11435/v1`。攔到的第一個對話請求：

```json
{"path": "/v1/chat/completions", "stream": true, "reasoning_effort": "none",
 "keys": ["messages","model","options","reasoning_effort","stream","stream_options","tools"],
 "n_tools": 20, "other": {"options": {"num_ctx": 262144}},
 "usage": {"prompt_tokens": 12983, "completion_tokens": 5}, "secs": 2.8}
```

`--reasoning none` 確實變成 `reasoning_effort: "none"`，這正是 Ollama OpenAI 相容端點關掉 Qwen 思考的方式（第五章 5-3-2）。不加的話預設是 `medium`，模型會先思考再呼叫工具，實測仍正確（18-8-1）。

### 18-7-2 64K context 的下限

Hermes 硬性要求模型 context ≥ 64,000。用 32K 的模型會在建立 agent 時直接失敗（CLI 只顯示「Something went wrong」，原因在 `~/.hermes/logs/gateway.log`）：

```sh
$ hermes chat --oneshot -Q -m hf.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF:Q4_K_M -q "回答一句話：你好。"
Error: ⚠️ Something went wrong and I couldn't finish this reply.
```

```
ValueError: Model hf.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF:Q4_K_M has a context window of 32,768 tokens,
which is below the minimum 64,000 required by Hermes Agent.  Your local server is serving a 32,768-token
window.  Start it with at least 64K context (llama.cpp: -c 64000; vLLM: --max-model-len;
Ollama: OLLAMA_CONTEXT_LENGTH=64000 or a Modelfile num_ctx), or set model.ollama_num_ctx in config.yaml
```

Hermes 讀的是 Ollama `/api/show` 回的 context length。qwen3.6 是 262,144 直接過關；GGUF 模型在 Ollama 的 llama.cpp runner 預設 32,768，要用就得用第五章 5-4-1 的方法調高（Modelfile `num_ctx 65536`，或 `model.ollama_num_ctx: 65536`）。64K 下限的原因：13K tokens 的 system prompt + 工具 schema，再加工具輸出與多輪對話，32K 很快就滿。

### 18-7-3 --oneshot 擋下的指令

一次性模式沒有人能按核准，`approvals.single_query_mode: deny` 會把所有需要核准的指令直接拒絕，模型會收到拒絕訊息並轉述：

```sh
$ mkdir -p /tmp/hermes_oneshot_test
$ hermes chat --oneshot -Q --reasoning none -q "請執行 rm -rf /tmp/hermes_oneshot_test 刪掉這個資料夾，然後告訴我結果。"
這是一支危險指令（`rm -rf`），本系統的 single-query mode 沒有使用者即時批准所以不允許執行。
可以改用以下安全替代做法達成同樣效果：
| `find /tmp -maxdepth 1 -name hermes_oneshot_test -type d -exec rm -rf {} +` | 只針對單一絕對路徑，不會觸發 blocked |
...
$ ls -d /tmp/hermes_oneshot_test
/tmp/hermes_oneshot_test            # 真的沒刪
```

值得注意：模型自己提出了用 `find ... -exec rm -rf` 繞過樣式比對的建議。這是 pattern 式核准的本質限制，所以不要在無人看管的模式用 `--yolo` 或 `approvals.mode: off`。

### 18-7-4 三種模型來源的比較

| 來源 | 設定 | 本機實測 |
|---|---|---|
| **Ollama 自訂端點** | `provider: custom`，`base_url: http://localhost:11434/v1` | 可用；一句話問答 7 秒、含一次工具呼叫 6 秒；Hermes 自動讀 context、送 `num_ctx` |
| Hermes Local models（代管 llama.cpp） | `hermes model` → Local models | 未安裝（本機模型由 Ollama 統一管理） |
| 雲端（Nous Portal / OpenRouter / Anthropic…） | `hermes model` 登入或填 key | 未使用；`hermes doctor` 顯示四個雲端供應者都 not logged in，不影響本機端點 |

## 18-8 已知問題

### 18-8-1 tool call 掉進 reasoning

原書的問題是：思考型模型把工具呼叫寫在 reasoning 內容裡而不是 `tool_calls` 欄位，agent 拿不到。**本機未重現**：預設 `reasoning_effort: medium`（思考開著）時，代理攔到的回應是 `resp_reasoning_chars: 124, resp_toolcall_deltas: 1, finish: tool_calls`，也就是思考內容和工具呼叫分別放在正確欄位。原因是 Ollama 0.40 對 Qwen3.6 用 `renderer/parser qwen3.5`（`ollama show` 可見），由伺服器端把 `<think>` 與工具呼叫解析成結構化欄位，不靠 Hermes 自己剖析文字。

兩個相關的實際問題：

1. **思考拖慢速度**：預設 medium 會多出數十到數百字的 reasoning，每輪多 1–2 秒；用 Qwen 寫程式建議 `--reasoning none` 或 `hermes config set agent.reasoning_effort none`。
2. **MLX runner 卡死**（第五章 5-6-3）：第一次 Hermes 查詢撞上 Ollama 的 MLX runner 卡住，花了 7 分 17 秒；runner 被砍掉後同樣的查詢 7 秒。

### 18-8-2 context 設定不一致

Hermes 和 Ollama 各有一套 context 設定，本機觀察到的對應關係：

| 位置 | 值 | 來源 |
|---|---|---|
| Ollama 模型原生 | 262,144 | `ollama show` |
| Hermes 讀到並快取 | 262,144 | log：`Cached context length ... -> 262,144 tokens` |
| Hermes 每個請求送的 `options.num_ctx` | 262,144 | 記錄代理 |
| Hermes 下限 | 64,000 | `_enforce_minimum_context` |

兩邊一致。會不一致的情況是 Ollama 這側用 `OLLAMA_CONTEXT_LENGTH` 或 Modelfile 把 context 調小，而 Hermes 仍以 `/api/show` 的模型原生值為準並送 `num_ctx`，結果是 Hermes 要求的值蓋過 Ollama 的設定、記憶體用量比預期高；要讓 Hermes 用較小值，改 `model.ollama_num_ctx`（或 `providers.<p>.models.<m>.context_length`）。

另一個本機實際踩到的不一致：**每輪對話結束後 Hermes 會用 `response_format: json_schema` 叫模型產生 session 標題**，MLX 模型不支援結構化輸出，Ollama 回 `501 structured output is unavailable`，Hermes 重試三次後放棄（`agent.log`：`Title generation failed: Error code: 501`）。不影響回答，但每輪多三個失敗請求。解法任一：

```sh
hermes config set auxiliary.title_generation.model_upgrade_enabled false   # 本機採用：改用即時推導的標題，不叫模型
# 或把標題生成指到一個 GGUF 模型（llama.cpp runner 支援 json_schema）：
# auxiliary.title_generation.model: <gguf 模型名>
```

設完後代理確認每輪只剩 `/api/show` 和一個 `/v1/chat/completions`，沒有 501。

### 18-8-3 Windows 原生的陷阱

**本機略過（Windows）。** macOS 這側唯一的「陷阱」是 shell：安裝腳本把 `~/.local/bin` 加進 `~/.zshrc` 和 `~/.zprofile`，已開著的終端機要 `source ~/.zshrc` 或重開才找得到 `hermes`。

## 18-9 本章小結

| 項目 | 結論 |
|---|---|
| 安裝 | 官方 `install.sh`（Homebrew formula 官方不支援）；v0.22.5；`hermes doctor` 全綠 |
| 接 Ollama | `model.provider custom` + `model.base_url http://localhost:11434/v1`；Hermes 會自動讀 context 並送 `num_ctx` |
| 速度 | 一句話 7 秒、含工具 6 秒；prompt 13K tokens，Ollama 快取讓第二輪起幾乎不重算 |
| 必要調整 | `--reasoning none`（或 `agent.reasoning_effort`）；`auxiliary.title_generation.model_upgrade_enabled false` |
| 限制 | 模型 context 必須 ≥ 64K（32K GGUF 直接失敗）；一次性模式拒絕所有需核准指令；MLX 不支援 json_schema |
| 未做 | 桌面版 GUI 流程、Local models 代管 runtime、LM Studio |
