# 第十九章：Hermes Agent 進階

> 延續第十八章的環境：Hermes Agent v0.22.5，模型 `qwen3.6:35b-a3b-coding-mxfp8`（Ollama 0.40.13，`--reasoning none`）。本章每個小節的指令與輸出都在這台 M5 Max 上實際執行；沒做的標「未驗證」或「本機略過」。所有測試都用一次性模式 `hermes chat --oneshot -Q -q "..."`，並透過第十八章的記錄代理觀察模型呼叫次數。

## 19-1 技能

### 19-1-1 技能的格式與位置

技能就是一個資料夾加一個 `SKILL.md`，YAML frontmatter 寫名稱、描述、適用平台與標籤，正文是給模型看的操作說明。本機自動建立的例子（19-1-2）：

```markdown
---
name: ollama-health-check
description: "Use when checking Ollama service: models, version, and logs."
version: "1.0.0"
author: Hermes Agent
platforms: [linux, macos]
metadata:
  hermes:
    tags: [ollama, health, diagnose, log]
    category: system
---

# Ollama Health Check

Run these three commands together to diagnose Ollama status:
1. `ollama ps` — list loaded models
2. `curl -s localhost:11434/api/version` — check Ollama API version
3. `tail -n 20 /opt/homebrew/var/log/ollama.log` — show recent logs
```

位置與來源（本機實際狀態）：

| 位置 | 內容 |
|---|---|
| `~/.hermes/skills/<分類>/<名稱>/SKILL.md` | 安裝時同步的 **58 個內建技能**，分類資料夾：`apple`、`autonomous-ai-agents`、`creative`、`devops`、`email`、`media`、`note-taking`、`productivity`、`research`、`social-media`、`software-development`、`web` |
| `~/.hermes/skills/<名稱>/SKILL.md` | agent 自己建立的技能（頂層，無分類資料夾） |
| `<專案>/.hermes/skills/` 或 `<專案>/.agents/skills/` | 專案技能，要先 `hermes skills trust` 才載入 |
| `~/.hermes/skills/.bundled_manifest` | 內建技能的雜湊，`hermes update` 用它判斷哪些被你改過、不覆蓋 |

```sh
$ hermes skills list
│ apple-notes      │ apple                │ builtin │ builtin │ enabled │
│ apple-reminders  │ apple                │ builtin │ builtin │ enabled │
│ claude-code      │ autonomous-ai-agents │ builtin │ builtin │ enabled │
│ codex            │ autonomous-ai-agents │ builtin │ builtin │ enabled │
...（共 58 個 builtin）
```

技能採「漸進揭露」：system prompt 裡只放技能索引（本機 5.6 KB），模型需要時再用 `skill_view` 讀全文，所以技能多也不會吃光 context。Frontmatter 的 `platforms: [macos]` 讓 Linux 上的 Hermes 看不到 Apple 專用技能。

### 19-1-2 自動建立與 Curator

**自動建立**：system prompt 要求模型在完成多步驟、可重複的流程後用 `skill_manage` 工具把它存成技能。本機直接要求它建立：

```sh
$ hermes chat --oneshot -Q --reasoning none -q "請用 skill_manage 建立一個名為 ollama-health-check 的 skill，內容是：用 'ollama ps' 檢查載入的模型、用 'curl -s localhost:11434/api/version' 檢查服務版本、用 'tail -n 20 /opt/homebrew/var/log/ollama.log' 看最近 log。建立後用一句話回報。"
Skill `ollama-health-check` 已建立，包含 `ollama ps`、`curl` 版本檢查、`tail` 查 log 三個診斷指令。
elapsed 14s
$ ls ~/.hermes/skills/ollama-health-check/
SKILL.md
```

代理攔到 9 次模型呼叫、8 次工具呼叫：模型先實際執行了那三個指令確認可用（terminal 工具），再呼叫 `skill_manage create`，最後回報。這就是「從經驗建技能」：它存的是跑過的流程，不是憑空寫的。要先審再寫：`hermes config set skills.write_approval true`，之後在對話裡用 `/skills pending`、`/skills approve <id>`。

**Curator** 是背景整理：追蹤技能使用、沒用的降級（active → stale → archived，歸檔到 `~/.hermes/skills/.archive/`，從不刪除），可選的 LLM 合併重複技能。本機狀態：

```sh
$ hermes curator status
curator: ENABLED
  runs:           0
  last run:       never
  interval:       every 7d
  stale after:    14d unused
  archive after:  30d unused
  consolidate:    off (prune-only; LLM merge pass opt-in)
unmanaged (no provenance marker): 1 total
  foreground-created  1          ← 就是剛建的 ollama-health-check
```

觸發條件是「距上次 ≥ 7 天且 agent 閒置 ≥ 2 小時」，在 CLI 啟動、gateway 例行維護時檢查；新安裝的第一次延後一個週期。手動：`hermes curator run --dry-run`、`hermes curator pin <skill>`（免於整理）、`hermes curator adopt <skill>`（把自建技能納管）。LLM 合併用的模型走 `auxiliary.curator`，預設跟主模型。

### 19-1-3 /learn 與 Skills Hub

**`/learn`**（**未驗證**：只能在互動 session 使用，一次性模式沒有斜線指令）：`/learn <本機路徑 | URL | 描述的流程>`，讓 agent 讀來源後用 `skill_manage` 存成技能；大型來源（整個文件資料夾）會變成「知識庫型技能」：精簡的 `SKILL.md` 加 `references/` 下的分主題檔。

**Skills Hub**：從多個來源搜尋與安裝別人寫的技能。本機搜尋 Ollama 相關：

```sh
$ hermes skills search ollama
Skills Hub — 25 result(s)
│ Ollama │ Run, tune, and troubleshoot local Ollama │ clawhub │ community │ ollama │
│ Ollama │ Ollama 本地大模型调用 … API 与 Ollama 实例交互 │ clawhub │ community │ ollama-2 │
...
$ hermes skills inspect <identifier>        # 看內容再決定
$ hermes skills install <identifier>        # 裝；community 來源會先做安全掃描，dangerous 判定無法用 --force 覆蓋
$ hermes skills check / update / uninstall <name>
```

來源有 `official`、`skills-sh`、`well-known`、`github`、`clawhub`（OpenClaw 的 hub）、`lobehub`、`browse-sh`；信任等級 `builtin` > `official` > `trusted` > `community`。本機沒有安裝任何 hub 技能。

## 19-2 記憶

### 19-2-1 MEMORY.md 與 USER.md

兩個純文字檔，整份注入每個 session 的 system prompt：

| 檔案 | 內容 | 上限（本機 `hermes config get`） |
|---|---|---|
| `~/.hermes/memories/MEMORY.md` | agent 的筆記（環境、流程、決定） | `memory.memory_char_limit` = 2,200 字元 |
| `~/.hermes/memories/USER.md` | 使用者側寫（偏好、背景） | `memory.user_char_limit` = 1,375 字元 |

模型透過 `memory` 工具寫入（`add` / `patch` / `remove`，`target` 為 `memory` 或 `user`）。本機實測：

```sh
$ hermes chat --oneshot -Q --reasoning none -q "請記住兩件事並寫進記憶：我叫 Rex，偏好繁體中文回答；這台電腦是 Apple M5 Max 128GB，Ollama 用 Homebrew 服務跑。寫完用一句話回報。"
已存檔：我的名字是 Rex（偏好繁體中文）；機型為 Apple M5 Max 128GB，Ollama 以 Homebrew 服務運行。
elapsed 5s
$ cat ~/.hermes/memories/USER.md
用戶名叫 Rex，偏好繁體中文回答。
$ cat ~/.hermes/memories/MEMORY.md
這台電腦是 Apple M5 Max 128GB，Ollama 透過 Homebrew 服務運行。
```

模型自己把兩件事分到正確的檔案（個人偏好 → USER，機器事實 → MEMORY）。安裝時這兩個檔不存在，第一次寫入才建立。要點：

- 超過上限的寫入會回錯誤而不是靜默丟棄，模型得先合併或刪舊的。
- 寫入立刻落盤，但**當前 session 的 system prompt 不會更新**，下一個 session 才看得到。
- 要先審核：`hermes config set memory.write_approval true`，之後 `/memory pending`、`/memory approve <id>`。

### 19-2-2 session 搜尋

所有對話（CLI 與訊息平台）存在 `~/.hermes/state.db`（SQLite + FTS5 全文索引），模型可用 `session_search` 工具查過去的對話。新開一個 session 問它：

```sh
$ hermes chat --oneshot -Q --reasoning none -q "用 session_search 工具查一下：我之前有沒有問過你 1+1 等於幾？找到的話說明是哪一次。"
找到了：1 次。
| 時間 | 2026-10-31 17:06 |
| 來源 | 一次性 session（oneshot） |
| 你的問題 | 「回答一句話：1+1 等於幾？不要用工具。」 |
| 我的回答 | `1+1=2` |
@session:default/local-c1fbc43191...
elapsed 5s
```

代理顯示它呼叫了兩次工具（搜尋、再讀該 session 內容）。CLI 端對應的是 `hermes sessions list`、`hermes --resume <id>`。

### 19-2-3 外部記憶後端與 ARM64

```sh
$ hermes memory status
  Built-in (MEMORY.md / USER.md):  Memory injection: enabled ✓  User profile: enabled ✓  Memory tool: enabled ✓
  Provider:  (none — built-in only)
  Installed plugins:
    • byterover  (API key / local)
    • retaindb  (API key / local)
```

內建記憶永遠開著；外部後端是**附加**的向量/圖記憶（RetainDB、ByteRover 隨附；Honcho、Mem0、Supermemory 等用 `hermes plugins install <name>`），用 `hermes memory setup` 啟用、一次只能一個。本機沒有啟用任何外部後端（**未驗證**）。原書的 ARM64 問題是 Windows on Arm 缺少某些後端的原生套件；macOS Apple Silicon 沒有這個問題，兩個隨附插件都已列在可用清單。

## 19-3 排程

### 19-3-1 建立排程工作

```sh
$ hermes cron create "every 6h" "檢查 ollama ps 有哪些模型載入，用一句話回報" --name ollama-check --deliver local
Created job: 902fceca1331
  Name: ollama-check
  Schedule: every 360m
  Next run: 2026-10-31T23:10:22+08:00
$ hermes cron list
  902fceca1331 [active]
    Name:      ollama-check
    Schedule:  every 360m
```

排程格式：一次性 `in 30m`、`2026-11-01T09:00:00`；週期 `every 2h`、`every monday 9am`、`weekdays at 9am`；或 cron 表達式 `0 9 * * 1-5`。對話裡也可以用自然語言（「每天早上九點…」）或 `/cron add`。

存放：`~/.hermes/cron/jobs.json`（定義）、`~/.hermes/cron/output/<job_id>/<時間>.md`（每次輸出）、`executions.db`（歷史）。本機 `jobs.json` 的這筆：

```json
{"id": "902fceca1331", "name": "ollama-check", "schedule": {"kind": "interval", "minutes": 360},
 "prompt": "檢查 ollama ps 有哪些模型載入，用一句話回報", "deliver": "local", "model": null, "enabled": true}
```

立刻跑一次驗證：

```sh
$ hermes cron run ollama-check
Triggered job: ollama-check
  Ran now: succeeded.
$ cat ~/.hermes/cron/output/902fceca1331/2026-10-31_17-13-05.md
## Response
目前 Ollama 載入了一個模型：qwen3.6:35b-a3b-coding-mxfp8（46 GB，完全使用 GPU 加速，262144 上下文，使用 MLX 運行器，4 分鐘後過期）。
```

兩個要點：

1. **排程由 gateway 執行**（每 60 秒 tick 一次）。CLI 對話時 Hermes 會自動起一個 `gateway run --idle-exit` 行程（`hermes gateway status` 顯示 `Running manually, not as a system service`），但要在沒開終端機時也準時執行，必須把 gateway 裝成服務（19-5-4）。
2. 排程裡的危險指令預設拒絕（`approvals.cron_mode: deny`），要讓無人看管的工作能執行需核准的指令，設成 `approve` 並確認 prompt 不會碰到危險操作。

管理：`pause` / `resume` / `edit --schedule "every 4h"` / `runs --limit 20` / `remove`。本章結束時已 `hermes cron remove ollama-check`。

### 19-3-2 排程用哪個模型

觸發當下依序決定：

1. 工作本身釘住的模型：`hermes cron create ... --model <m> --provider <p>`（或之後 `--pin`）。
2. 排程整體預設：`hermes config set cron.model <m>`（本機未設，空字串）。
3. 都沒有就用主模型（`model.default`）。上面那次執行 `jobs.json` 的 `model` 是 `null`，所以用了 qwen3.6。

對這台機器的建議：排程多半是短任務，可以釘到較小、載入快的模型，避免半夜為了一句話載入 38 GB；但注意 Hermes 的 64K context 下限（18-7-2），模型要先在 Ollama 側設好 `num_ctx`。

## 19-4 MCP 與子 Agent

### 19-4-1 接上 MCP 伺服器

Hermes 有一個 Nous 審核過的 MCP 型錄，一行安裝；本機裝一個不需帳號的遠端 HTTP 伺服器 DeepWiki（讀 GitHub repo 的文件）：

```sh
$ hermes mcp catalog | head          # airtable, algolia, asana, atlassian, aws-knowledge, ...
$ hermes mcp install deepwiki
  ✓ Installed 'deepwiki' (enabled). Start a new Hermes session to load its tools.
$ hermes mcp test deepwiki
  Transport: HTTP → https://mcp.deepwiki.com/mcp   Auth: none
  ✓ Connected (2746ms)
  ✓ Tools discovered: 3
    ask_wiki_question / read_wiki_contents / read_wiki_structure
```

寫進 `config.yaml` 的只有：

```yaml
mcp_servers:
  deepwiki:
    url: https://mcp.deepwiki.com/mcp
    enabled: true
```

自己接任何伺服器就是在這個區塊加一筆：stdio 用 `command` + `args`（+ `env`），HTTP 用 `url` + `headers`，OAuth 加 `auth: oauth`；`tools: {include: [...]}` / `exclude` 過濾工具。工具名稱會變成 `mcp_<server>_<tool>`，整個伺服器變成一個 `mcp-<server>` toolset。實際呼叫：

```sh
$ hermes chat --oneshot -Q --reasoning none -q "用 deepwiki 的 read_wiki_structure 工具查 NousResearch/hermes-agent 這個 repo 有哪些文件主題，列出前五個。"
| 1 | Overview | 2 |
| 2 | Getting Started | 4 |
| 3 | CLI | 4 |
| 4 | Core Agent | 5 |
| 5 | Tool System | 8 |
elapsed 4s
```

代理顯示工具數從 20 變 21（多了 `tool_search` 可找到的 MCP 工具），兩次工具呼叫後回答。安全面：MCP 子行程只拿到 `PATH`、`HOME`、`USER`、`LANG`、`TERM` 等少數環境變數加伺服器自己 `env` 裡的值，`hermes doctor` 會檢查 stdio 指令是否可疑。

### 19-4-2 delegate_task

模型可以用 `delegate_task` 開子 agent：各自獨立的對話、受限的工具（leaf 子 agent 不能再 delegate、不能寫 memory、不能發訊息），結果回到父 agent。本機強制它平行開兩個：

```sh
$ hermes chat --oneshot -Q --reasoning none -q "請用 delegate_task 同時開兩個子任務：子任務一計算 2 的 10 次方，子任務二計算 3 的 5 次方；拿到結果後彙整成一句話。"
子任務已完成：
- 2 的 10 次方 = 1024
- 3 的 5 次方 = 243
elapsed 9s
```

代理攔到的請求清楚看出父子結構：父 agent 的請求帶 21 個工具、約 14.4K prompt tokens；兩個子 agent 的請求各帶 **17 個工具、約 10.8K tokens**（少了 delegate/memory/clarify 等被禁的工具），每個子 agent 用 3 次呼叫（算、驗證、回答）完成，再由父 agent 彙整。全部 10 次模型呼叫、9 秒。

設定：`delegation.max_concurrent_children`（本機預設 **10**）、`delegation.model` / `delegation.provider`（子 agent 用別的模型，例如把子任務丟給較小的模型；未設則跟父）、`delegation.max_spawn_depth`（預設 1，子不能再生孫）。對話中 `/agents`（或 Ctrl+T）看執行中的子 agent，`/stop` 中止。

## 19-5 訊息平台

### 19-5-1 gateway

gateway 是一個長駐行程，同時負責：接訊息平台（Telegram、Discord、Slack、LINE、Signal、Email… 近 30 種）、跑排程、處理 webhook。本機狀態：

```sh
$ hermes gateway status
✓ Gateway is running (PID 29917)
  (Running manually, not as a system service)
$ ps -o command= -p 29917
python3 -m hermes_cli.main --profile default gateway run --quiet --idle-exit
```

這個行程是第一次 `hermes chat` 時自動起的（`--idle-exit`：閒置一段時間自己結束）。要長駐見 19-5-4。平台設定走互動精靈 `hermes gateway setup`，或直接寫 `~/.hermes/.env`（token）與 `config.yaml` 的 `gateway.platforms`。本機沒有任何平台的 token，19-5-2、19-5-3 只能驗證到設定項與 `hermes doctor` 的套件檢查（`python-telegram-bot` 顯示 optional, not installed，設定 Telegram 時才會裝）。

### 19-5-2 Telegram

**未驗證（沒有 bot token）。** 官方步驟：

1. Telegram 找 @BotFather → `/newbot` → 取得 token；找 @userinfobot 取得自己的數字 user id。
2. `hermes gateway setup` 選 Telegram 填入，或手動寫 `~/.hermes/.env`：
   ```
   TELEGRAM_BOT_TOKEN=<token>
   TELEGRAM_ALLOWED_USERS=<你的 user id，逗號分隔多個>
   ```
3. `hermes gateway run`（前景）或 `hermes gateway start`（服務），對 bot 傳訊息測試。
4. 選用：在想收排程結果的聊天裡送 `/sethome`，或設 `TELEGRAM_HOME_CHANNEL=<chat id>`。

沒在白名單的人傳訊會收到配對碼，你在終端機 `hermes pairing approve telegram <CODE>` 才放行；配對碼一小時過期。桌面版 / dashboard 的 Messaging → Telegram 頁有「Create with QR」可以自動建 bot 並寫入這兩個變數。

### 19-5-3 LINE

**未驗證（沒有 LINE 官方帳號）。** 和 Telegram 的差別是 LINE 用 **webhook**，Hermes 必須有一個公開的 HTTPS 網址：

1. LINE Developers Console 建 Provider → Messaging API channel；複製 **Channel secret**，發一個長效 **Channel access token**；關掉自動回覆與歡迎訊息。
2. 把本機的 webhook 埠（預設 8646，`LINE_PORT` 可改）打到公網：`cloudflared tunnel --url http://localhost:8646`（建議）或 `ngrok http 8646`。
3. `~/.hermes/.env`：
   ```
   LINE_CHANNEL_ACCESS_TOKEN=...
   LINE_CHANNEL_SECRET=...
   LINE_ALLOWED_USERS=U...          # 或 LINE_ALLOWED_GROUPS=C... / LINE_ALLOWED_ROOMS=R...
   LINE_PUBLIC_URL=https://<tunnel>  # 傳圖片/語音才需要
   ```
   `config.yaml`：`gateway.platforms.line.enabled: true`。
4. Console 的 Webhook URL 填 `https://<tunnel>/line/webhook`，按 Verify、開啟 Use webhook。
5. `hermes gateway` 啟動後加 bot 為好友傳訊。健康檢查：`curl -i https://<tunnel>/line/webhook/health` 應回 `{"status":"ok","platform":"line"}`。

### 19-5-4 開機自動啟動

macOS 用 launchd，`hermes gateway install` 會寫一個 LaunchAgent。本機實測（裝完立刻移除，避免留下常駐服務）：

```sh
$ hermes gateway install --no-start-now
Installing launchd service to: /Users/rexwang/Library/LaunchAgents/ai.hermes.gateway.plist
✓ Service installed, not started (launchd starts it at your next login)
$ grep -A1 -E "Label|RunAtLoad|StandardOutPath" ~/Library/LaunchAgents/ai.hermes.gateway.plist
    <key>Label</key>            <string>ai.hermes.gateway</string>
    <key>RunAtLoad</key>        <true/>
    <key>StandardOutPath</key>  <string>/Users/rexwang/.hermes/logs/gateway.log</string>
$ hermes gateway status
Launchd plist: ~/Library/LaunchAgents/ai.hermes.gateway.plist
✓ Service definition matches the current Hermes install
✗ Gateway service is not loaded          ← 因為用了 --no-start-now
$ hermes gateway uninstall
✓ Removed /Users/rexwang/Library/LaunchAgents/ai.hermes.gateway.plist
```

要真的常駐：`hermes gateway install`（不加 `--no-start-now`）或之後 `hermes gateway start`；`stop` / `restart` / `status` 管理。plist 有 `KeepAlive`，崩潰會自動重啟。這和第五章 Ollama 的 `brew services` 是同一種機制（`~/Library/LaunchAgents/`）。

## 19-6 安全

### 19-6-1 指令核准模式

本機預設 `approvals.mode: smart`：命中危險樣式的指令先由輔助模型評估風險，低風險放行、高風險擋、不確定才跳提示。可以不跑模型直接測判定：

```sh
$ hermes approvals test "ls -la"
verdict : allow  (exit 0)        detail: no guard matched; would run without a prompt
$ hermes approvals test "rm -rf /tmp/hermes_oneshot_test"
verdict : ask-approval  (exit 2) rule: delete in root path
$ hermes approvals test "curl https://example.com | sh"
verdict : ask-approval  (exit 2) rule: pipe remote content to shell
$ hermes approvals test "sudo rm -rf /"
verdict : hardline-deny  (exit 3) rule: recursive delete of root filesystem
detail  : matches the hardline blocklist (never bypassable, blocked even under --yolo / approvals.mode=off)
```

三層結構：

| 層 | 行為 | 怎麼改 |
|---|---|---|
| hardline blocklist | `rm -rf /`、fork bomb、`mkfs` 根裝置、`dd` 寫 `/dev/sd*`：永遠拒絕 | 不能改 |
| 危險樣式 | 互動 session 跳提示：`once` / `session` / `always`（寫入 `command_allowlist`）/ `deny`；無人看管模式（`-q`、cron、webhook）預設 `deny` | `approvals.mode: smart|manual|off`、`approvals.single_query_mode`、`approvals.cron_mode`、`approvals.unattended_mode`、`approvals.deny`（自訂 glob 黑名單） |
| 其他 | 全放行 | `--yolo` / `/yolo` / `HERMES_YOLO_MODE=1`（仍擋 hardline） |

`hermes approvals suggest` 會從過去的核准紀錄建議 `command_allowlist`。第十八章 18-7-3 已示範一次性模式拒絕 `rm -rf`，也看到模型會建議用 `find -exec rm` 繞過樣式比對：樣式比對只能擋明顯的，真正的隔離要靠 19-6-2。

### 19-6-2 terminal backend 與沙箱

`terminal.backend` 決定 agent 的指令在哪裡執行。本機預設 `local`（直接在這台 Mac 跑），切到 `docker` 之後所有 terminal / 檔案 / `execute_code` 呼叫都進同一個長壽容器：

```sh
$ hermes config get terminal.docker_image
nousresearch/hermes-sandbox:desktop
$ hermes config set terminal.backend docker
$ hermes gateway stop                      # 重要：見下方第 1 點
$ hermes chat --oneshot -Q --reasoning none -q "用 terminal 工具執行 uname -a 以及 cat /etc/os-release | head -2，原文貼給我。"
Linux bf94daa453bc 7.0.14-linuxkit #1 SMP PREEMPT Fri Oct 16 11:55:50 UTC 2026 aarch64 GNU/Linux
PRETTY_NAME="Debian GNU/Linux 13 (trixie)"
elapsed 107s                               # 含第一次拉 4.38 GB 映像檔
$ docker ps --format '{{.Names}} {{.Image}} {{.Status}}'
hermes-a179476c nousresearch/hermes-sandbox:desktop Up 1 second
```

`gateway.log` 記下了容器的啟動參數，可以看到它怎麼收緊權限：

```
Docker run_args: ['--cap-drop', 'ALL', '--cap-add', 'DAC_OVERRIDE', '--cap-add', 'CHOWN', '--cap-add', 'FOWNER',
                  '--tmpfs', '/tmp:rw,nosuid,size=512m', '--tmpfs', '/var/tmp:rw,noexec,nosuid,...', ...]
Docker volume_args: ['-v', '/Users/rexwang/.hermes/skills:/root/.hermes/skills:ro', '-v', '.../cache/documents:...:ro', ...]
Ignoring TERMINAL_CWD='/Users/rexwang' for docker backend (host/relative path won't work in sandbox). Using '/root' instead.
```

本機實測踩到的兩點：

1. **第一次切換沒生效。** 改完 `terminal.backend` 直接跑，`uname -a` 回的是 `Darwin`（macOS）：Hermes 的 gateway 行程還在跑舊設定，而且背景正在拉映像檔。`hermes gateway stop`（或 `restart`）之後再跑才進容器。要先 `docker pull nousresearch/hermes-sandbox:desktop` 把 4.38 GB 拉好，不然第一個任務會等很久。
2. **容器裡的危險指令不會再問。** 官方規則是「容器本身就是邊界」：`docker`、`modal`、`daytona`、`vercel_sandbox`、`singularity` 後端都跳過 19-6-1 的核准檢查。所以 Docker 後端適合讓 agent 自由安裝套件、改檔案，但掛進去的 `~/.hermes/skills` 等目錄是唯讀的；要讓它改專案，用 `terminal.cwd` 指定工作目錄並留意掛載。

後端一覽（本機只測了 `local` 與 `docker`）：

| 後端 | `terminal.backend` | 隔離程度 | 本機 |
|---|---|---|---|
| 本機 | `local` | 無，靠核准模式 | 預設，實測 |
| Docker | `docker` + `terminal.docker_image` | 容器：cap-drop ALL、唯讀掛載、tmpfs | 實測可用（Docker Desktop 29.9.2） |
| SSH | `ssh` + `TERMINAL_SSH_HOST/USER/KEY` | 另一台機器；官方建議用它讓 agent 碰不到自己的程式碼 | 未驗證 |
| Modal / Daytona / Vercel Sandbox | `modal` / `daytona` / `vercel_sandbox` | 雲端沙箱，需各自帳號 | 未驗證 |

資源與持久化：`terminal.container_cpu`（預設 1）、`container_memory`（5120 MB）、`container_disk`（51200 MB）、`container_persistent`（true：容器在 Hermes 行程存活期間保留，裝過的套件不用重裝）。本機 log 有一行 `Cgroup limit probe failed; containers run without CPU/memory/PID limits until a probe succeeds`：Docker Desktop on macOS 的 cgroup 探測失敗，所以 CPU / 記憶體上限暫時沒套用，隔離仍在。測完已改回 `local`，容器用 `docker rm -f hermes-a179476c` 清掉。

### 19-6-3 搭配 OpenShell

**未驗證（未安裝）。** OpenShell 是 NVIDIA 的 agent 沙箱：用政策檔宣告 agent 能連哪些網域、碰哪些路徑，核心層強制執行，API key 留在沙箱外由 gateway 代注入，政策變更先經形式驗證。官方支援 Linux、**macOS Apple Silicon**、Windows WSL2（實驗性），需要 Docker / Podman。NVIDIA 的 NemoClaw 可以一行把 Hermes 部署進 OpenShell（`nemohermes` 是預選 Hermes 的別名），Hermes 設定在沙箱內 `/sandbox/.hermes`，推論可路由到本機 Ollama。安裝方式是 `curl ... | sh` 腳本；本機因政策不由 Claude Code 執行外部安裝腳本，未安裝。和 19-6-2 的 Docker 後端相比，OpenShell 多了**網路出口政策**與**憑證不進沙箱**兩件事。

## 19-7 本章小結

| 主題 | 本機結論 |
|---|---|
| 技能 | 58 個內建 + agent 自建（實測 14 秒建一個，先執行過再存）；Curator 7 天一次整理，從不刪除 |
| 記憶 | `USER.md` / `MEMORY.md` 各 1,375 / 2,200 字元上限，模型會自己分類；session 全文搜尋可用 |
| 排程 | `hermes cron create` + gateway；立即執行驗證成功；無人看管時危險指令預設拒絕 |
| MCP / 子 Agent | 型錄一行裝 DeepWiki 並成功呼叫；delegate_task 開兩個子 agent（17 工具、10.8K tokens）9 秒完成 |
| 訊息平台 | gateway 自動啟動；launchd 安裝/移除驗證；Telegram / LINE 僅文件（無 token） |
| 安全 | smart / manual / off 三種核准模式 + hardline blocklist；`hermes approvals test` 可離線測；Docker 後端實測進 Debian 13 容器（改設定後要重啟 gateway） |
| 未做 | `/learn`（需互動 session）、外部記憶後端、OpenShell |
