# 第五章：Ollama

本章所有指令與輸出都在下面這台電腦上實際執行過（2026-10-31）。沒有驗證到的項目會明確標示「未驗證」。原書 Windows / CUDA 專屬的內容（illegal memory access 等）不在本教材範圍。

| 項目 | 規格 |
|---|---|
| 晶片 | Apple M5 Max（`uname -m` → `arm64`） |
| 記憶體 | 128 GB 統一記憶體 |
| 系統 | macOS 27.2 |
| Ollama | 0.40.13（Homebrew formula，背景服務） |
| Python | 3.15.2（`/opt/homebrew/bin/python3`） |
| Docker | Docker Desktop 29.9.2 |

範例程式在 [`examples/ch05/`](../examples/ch05/)。

---

## 5-1 安裝 Ollama

### 5-1-1 Arm64 版與 x64 版

macOS 上的 Ollama 只有一個 Apple Silicon 原生版本，沒有「選 x64 或 Arm64」的問題。Homebrew 裝在 `/opt/homebrew`，就是 arm64 前綴（Intel Mac 的 Homebrew 在 `/usr/local`），裝出來的 binary 也是 arm64：

```sh
$ uname -m
arm64
$ file /opt/homebrew/bin/ollama
/opt/homebrew/bin/ollama: Mach-O 64-bit executable arm64
```

不需要 Rosetta。

兩種安裝方式，擇一即可：

| 方式 | 指令 | 特點 |
|---|---|---|
| **formula（本機採用）** | `brew install ollama` + `brew services start ollama` | 純 CLI + launchd 背景服務，開機自動啟動，log 在 `/opt/homebrew/var/log/ollama.log` |
| cask | `brew install --cask ollama-app` | 選單列 App，自動更新，內建聊天視窗 |

本機實際狀態：

```sh
$ ollama --version
ollama version is 0.40.13
$ brew services info ollama
ollama (sh.brew.ollama)
Running: true
Loaded: true
User: rexwang
PID: 10789
$ lsof -nP -iTCP:11434 -sTCP:LISTEN
ollama  10789 rexwang ... TCP 127.0.0.1:11434 (LISTEN)
```

Homebrew 產生的服務設定檔是 `~/Library/LaunchAgents/sh.brew.ollama.plist`，裡面預先帶了兩個環境變數（5-4-2 會談）：

```xml
<key>EnvironmentVariables</key>
<dict>
    <key>OLLAMA_FLASH_ATTENTION</key><string>1</string>
    <key>OLLAMA_KV_CACHE_TYPE</key><string>q8_0</string>
</dict>
```

### 5-1-2 確認用到 GPU

三個地方可以確認。

**1. 服務啟動時的 log**：Ollama 偵測到 Metal GPU，可用記憶體 107.5 GiB。

```sh
$ grep -E "inference compute|default context" /opt/homebrew/var/log/ollama.log | tail -2
... msg="inference compute" id=0 library=Metal name=MTL0 description="Apple M5 Max" type=iGPU total="107.5 GiB" available="107.5 GiB"
... msg="vram-based default context" total_vram="107.5 GiB" default_num_ctx=262144
```

注意：128 GB 的機器，Ollama 看到的 GPU 可用記憶體是 **107.5 GiB**（約 84%），不是常被引用的 75%。這是 macOS 預設的 GPU wired 上限（`sysctl iogpu.wired_limit_mb` 為 0 表示用系統預設）。

**2. 模型載入後的 `ollama ps`**：`PROCESSOR` 欄 `100% GPU`，`RUNNER` 欄會顯示用哪個引擎。

```
$ ollama ps
NAME                            ID              SIZE     PROCESSOR    CONTEXT    RUNNER    UNTIL
qwen3.6:35b-a3b-coding-mxfp8    47f49b2845d7    38 GB    100% GPU     262144     mlx       4 minutes from now
```

**3. 模型載入的 log**：

```
msg="starting mlx runner subprocess" model=qwen3.6:35b-a3b-coding-mxfp8
msg="MLX engine initialized" "MLX version"=0.32.4 device=gpu
```

Ollama 0.40 在 Apple Silicon 上有兩種 runner：

| RUNNER | 用於 | 本機實例 |
|---|---|---|
| `mlx` | safetensors 格式（mxfp8、nvfp4、bf16、`-mlx` 標籤） | `qwen3.6:35b-a3b-coding-mxfp8` |
| `llamacpp` | GGUF 格式（q4_K_M、q8_0 等） | `qwen3-embedding:0.6b`、匯入的 GGUF |

### 5-1-3 模型存放位置

```sh
$ ls ~/.ollama
cache  id_ed25519  id_ed25519.pub  models
$ ls ~/.ollama/models
blobs  manifests  manifests-v2  qwen3.6
$ du -sh ~/.ollama/models
 36G
```

- `blobs/`：實際權重，檔名是 `sha256-...`。不同標籤若共用同一層權重，只會存一份。
- `manifests/registry.ollama.ai/library/<模型>/<標籤>`：標籤對應哪些 blob。
- `ollama create` 產生的衍生模型只多一個 manifest 和一小層參數 blob，不會複製 38 GB 的權重。

改位置：設定 `OLLAMA_MODELS=/Volumes/外接碟/ollama`（設法見 5-3-3）。本機沒有改。

---

## 5-2 下載與執行模型

### 5-2-1 ollama run

`ollama run` 會在需要時自動 `pull`。三種用法：

```sh
# 單次問答（適合腳本），--verbose 印出速度統計
$ ollama run qwen3.6:35b-a3b-coding-mxfp8 --think=false --verbose "用一句話說明什麼是 Ollama。"
Ollama 是一個讓開發者和普通用戶能在本地電腦上輕鬆下載、運行和管理大型語言模型（LLM）的開源工具。

total duration:       4.933114917s
load duration:        4.612660875s
prompt eval count:    21 token(s)
prompt eval rate:     342.12 tokens/s
eval count:           31 token(s)
eval rate:            119.86 tokens/s

# 從 stdin 餵內容
$ cat main.py | ollama run qwen3.6:35b-a3b-coding-mxfp8 --think=false "找出這段程式的 bug"

# 互動模式
$ ollama run qwen3.6:35b-a3b-coding-mxfp8
>>> Send a message (/? for help)
```

載入 38 GB 模型花 4.6 秒，之後生成速度約 **120 tokens/s**（第二次起 `load duration` 接近 0）。

互動模式的指令（`/?` 的實際輸出）：

| 指令 | 功能 |
|---|---|
| `/set parameter num_ctx 32768` | 設定參數（也可設 `temperature`、`num_predict`…） |
| `/set system <string>` | 設定 system prompt |
| `/set think` / `/set nothink` | 開關思考模式 |
| `/set verbose` / `/set quiet` | 顯示 / 隱藏速度統計 |
| `/set format json` / `/set noformat` | JSON 模式（MLX 模型不支援，見 5-6） |
| `/show info` `/show parameters` `/show system` `/show template` `/show modelfile` `/show license` | 查看模型資訊 |
| `/save <name>` / `/load <name>` | 把目前對話（含 system、參數）存成新模型 / 載回 |
| `/clear` | 清除對話 context |
| `/bye` 或 Ctrl-D | 離開 |
| `"""` | 開始多行輸入 |
| `/path/to/img.png` | 直接打路徑就能附圖（.jpg .png .webp；.wav 音訊） |

快捷鍵：Ctrl-A/E 行首行尾、Ctrl-K/U 刪到行尾/行首、Ctrl-W 刪前一個字、Ctrl-L 清畫面、Ctrl-G 用 `$EDITOR` 編輯提示、Ctrl-C 中斷生成。

這台機器的主力模型預設**會思考**（`ollama show` 的 `thinking default: true`），寫程式類問答建議加 `--think=false`，速度快很多；要看推理過程再打開。

### 5-2-2 選擇模型與量化

模型大小 ≈ 參數量 × 每個參數的位元數 / 8，再加 KV cache。同一個模型在 Ollama 庫裡會有很多標籤，差別就在量化格式。以 `qwen3.6` 為例（2026-10-31 從 ollama.com/library/qwen3.6/tags 抓到的實際大小）：

| 標籤 | 大小 | 格式 / runner | 說明 |
|---|---|---|---|
| `35b-a3b-mtp-q4_K_M` | 23 GB | GGUF / llamacpp | 4-bit，最省；mtp = 有多 token 預測草稿層 |
| `35b-a3b-nvfp4` | 23 GB | safetensors / mlx | 4-bit 浮點 |
| `35b-a3b-mxfp8`（**本機主力，coding 版**） | 38 GB | safetensors / mlx | 8-bit 浮點，品質接近原始 |
| `35b-a3b-q8_0` | 39 GB | GGUF / llamacpp | 8-bit 整數 |
| `35b-a3b-bf16` | 72 GB | safetensors / mlx | 未量化 |
| `27b-q4_K_M` | 17 GB | GGUF | Dense 27B，4-bit |
| `27b-coding-mxfp8` | 30 GB | safetensors / mlx | Dense 27B，8-bit |
| `27b-bf16` | 56 GB | safetensors | Dense 27B 未量化 |

挑法（128 GB、GPU 上限 107.5 GiB）：

1. **先決定 Dense 還是 MoE。** `35b-a3b` 是 MoE：總參數 36B，但每個 token 只啟用約 3B，所以 38 GB 的模型能跑 120 tokens/s。Dense 27B 每個 token 要讀完整 27B 參數，同樣 8-bit 會慢約一半以上（未實測）。
2. **再決定精度。** 記憶體夠就選 8-bit（mxfp8 / q8_0），和 bf16 幾乎沒差；4-bit 省一半空間但品質會掉一些。
3. **留空間給 KV cache 和其他程式。** 38 GB 的模型 + 256K context 的快取 + Docker + IDE，在 128 GB 上還很寬裕；84 GB 的模型（5-2-4）就只能單獨跑。
4. **格式決定 runner。** safetensors 走 MLX（Apple 原生，速度好），GGUF 走 llama.cpp（功能最完整，例如 structured output，見 5-6）。

查一個模型的詳細資訊：

```sh
$ ollama show qwen3.6:35b-a3b-coding-mxfp8
  Model
    architecture        qwen3_5_moe
    parameters          36.0B
    context length      262144
    quantization        mxfp8
  Capabilities
    completion  vision  tools  thinking
  Parameters
    temperature 0.6  top_k 20  top_p 0.95  min_p 0  repeat_penalty 1
  License
    Apache License Version 2.0
```

本機 `ollama list`（含本章測試時拉的小模型）：

```
NAME                                            ID              SIZE
embeddinggemma:latest                           85462619ee72    621 MB
hf.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF:Q4_K_M    002f8862bb2b    491 MB
qwen3-embedding:0.6b                            ac6da0dfba84    639 MB
qwen3.6:35b-a3b-coding-mxfp8                    47f49b2845d7    38 GB
```

### 5-2-3 同時載入多個模型

Ollama 預設允許多個模型同時在記憶體裡（`OLLAMA_MAX_LOADED_MODELS` 預設 0 = 自動，單 GPU 為 3 個），記憶體不夠時才會把最久沒用的卸載。實測三個模型同時在 GPU 上：

```
$ ollama ps
NAME                                            SIZE      PROCESSOR    CONTEXT    RUNNER      UNTIL
hf.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF:Q4_K_M    602 MB    100% GPU     32768      llamacpp    4 minutes from now
qwen3.6:35b-a3b-coding-mxfp8                    39 GB     100% GPU     262144     mlx         4 minutes from now
coder:latest                                    38 GB     100% GPU     32768      mlx         3 minutes from now
```

兩個要點：

- 每個模型是**獨立的 runner 子行程**（`ollama runner --model ...` 或 `llama-server`），MLX 和 llama.cpp 可以混用。
- `coder` 是用 Modelfile 從 `qwen3.6` 衍生的（5-5-1）。磁碟上共用權重，**但載入記憶體時是兩份**，上面就吃了 77 GB。衍生模型和原模型不要同時用。

同一個模型的平行請求數由 `OLLAMA_NUM_PARALLEL` 控制（本機 log 顯示預設 1）。

### 5-2-4 執行 Nemotron 3.5 Super VL

Ollama 庫的名稱是 `nemotron-3.5-super`（沒有 `-vl` 後綴，但 manifest 含 1.61 GiB 的 vision projector，就是 VL 版）。從 registry manifest 查到的實際大小：

| 模型 | 大小 | 本機可否執行 |
|---|---|---|
| `nemotron-3.5-super` | 84.0 GiB（model 82.35 + projector 1.61） | 可以，但要獨佔 GPU（107.5 GiB 上限） |
| `nemotron-3-super` | 80.9 GiB | 同上 |
| `nemotron-3-nano` | 22.6 GiB | 可以，可與主力模型共存 |

```sh
ollama pull nemotron-3.5-super
```

本機以約 6–11 MB/s 下載 79 GB，需 2–3 小時。**執行結果：待下載完成後補上**（這一節的速度、記憶體與 `ollama ps` 數字尚未驗證）。預期行為：載入時 Ollama 會先卸載 38 GB 的 qwen3.6，因為 84 + 38 > 107.5。

---

## 5-3 API

服務只聽 `127.0.0.1:11434`。所有端點都不需要認證。

### 5-3-1 原生 API

| 端點 | 用途 |
|---|---|
| `GET /api/version` | 版本 → `{"version":"0.40.13"}` |
| `GET /api/tags` | 已下載模型 |
| `GET /api/ps` | 載入中的模型（含 `size_vram`、`context_length`、`runner`、`expires_at`） |
| `POST /api/generate` | 單輪生成，無對話歷史 |
| `POST /api/chat` | 多輪對話、工具呼叫、圖片 |
| `POST /api/embed` | 向量 |
| `POST /api/show` | 模型資訊 |
| `POST /api/pull` `/api/create` `/api/copy` `DELETE /api/delete` | 模型管理 |

**generate**（[`01_api_generate.sh`](../examples/ch05/01_api_generate.sh) 實際輸出）：

```sh
curl -s http://localhost:11434/api/generate -d '{
  "model": "qwen3.6:35b-a3b-coding-mxfp8",
  "prompt": "用一句話解釋什麼是 MoE 模型。",
  "stream": false, "think": false }'
```
```
MoE（混合專家模型）是一種通過「門控機制」在推理時動態選擇部分專屬專家網絡來處理輸入數據的大語言模型架構…
--- 43 tokens, 116.3 tok/s
```

回應裡的 `eval_count / eval_duration`（奈秒）就是生成速度。`stream` 預設 `true`，每個 token 一行 JSON。

**chat**（[`02_api_chat.sh`](../examples/ch05/02_api_chat.sh)）：對話歷史由呼叫端自己放在 `messages` 陣列裡。

```
$ ./02_api_chat.sh
你剛剛說你叫 Rex。
```

**思考模式**：`"think": false` 關閉，`true` 開啟；支援等級的模型可給 `"low"/"medium"/"high"`。開著的時候回應多一個 `thinking` 欄位。

**工具呼叫**：`tools` 用 OpenAI 的 function schema，模型回 `message.tool_calls`，執行後以 `{"role":"tool","tool_name":...,"content":...}` 回傳。完整的 Agent 迴圈在 [`04_tools_agent.py`](../examples/ch05/04_tools_agent.py)，實測一次問三件事，模型連續呼叫三個工具後整合回答：

```
$ python 04_tools_agent.py "現在幾點？順便算一下 2 的 20 次方，然後列出目前資料夾的檔案"
  ↳ 呼叫 get_current_time({})
  ↳ 呼叫 calculate({"expression": "2 ** 20"})
  ↳ 呼叫 list_directory({"path": "."})
現在的時間是 2026-10-31 16:27:21。
2 的 20 次方等於 1,048,576。
目前資料夾內的檔案與子資料夾包括：...
```

**圖片**：`messages[].images` 放檔案路徑或 base64（[`07_vision.py`](../examples/ch05/07_vision.py)，程式自己產生一張紅底藍方塊的 PNG）：

```
這是一個藍色的正方形，位於紅色的背景中央。
```

**向量**：

```sh
$ curl -s localhost:11434/api/embed -d '{"model":"qwen3-embedding:0.6b","input":["本機模型","Ollama 是什麼"]}'
→ 2 個向量，每個 1024 維
```

**結構化輸出（`format`）**：本機主力模型**不支援**，見 5-6-1。

### 5-3-2 OpenAI 相容端點

`http://localhost:11434/v1`，`api_key` 隨便填。實測可用：`/v1/models`、`/v1/chat/completions`（含 stream、tools）。

```sh
$ curl -s localhost:11434/v1/models | python3 -m json.tool
{"object": "list", "data": [{"id": "qwen3.6:35b-a3b-coding-mxfp8", "object": "model", "owned_by": "library"}]}
```

**本機最重要的坑**：走 `/v1` 時 `"think": false` 會被忽略，模型照樣思考，`max_tokens` 先被思考內容吃掉，`content` 是空字串、`finish_reason` 是 `length`：

```json
"message": {"role": "assistant", "content": "", "reasoning": "Here's a thinking process:\n\n1. **Analyze User Input:** ..."},
"finish_reason": "length"
```

改用 `"reasoning_effort": "none"` 才會關掉：

```json
"message": {"role": "assistant", "content": "Hi, how are you?"}, "finish_reason": "stop"
```

Python 用官方 `openai` 套件（[`05_openai_compat.py`](../examples/ch05/05_openai_compat.py)，實際輸出）：

```python
client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
client.chat.completions.create(model=MODEL, messages=[...], reasoning_effort="none", stream=True)
```
```
== 串流回答 ==
Apple Silicon 採用統一記憶體架構，讓處理器核心的 CPU、GPU 及其他單元共享同一塊高速記憶體池…
== 工具呼叫 ==
get_weather {"city":"高雄"}
```

### 5-3-3 開放給區域網路

預設只聽 `127.0.0.1`。要讓同網段的其他機器（或 Docker 以外的裝置）連進來，把 `OLLAMA_HOST` 設成 `0.0.0.0`。

Homebrew 服務的環境變數不要直接改 plist（`brew services restart` 會從 formula 重新產生而覆蓋掉），改用 launchd 的使用者環境：

```sh
launchctl setenv OLLAMA_HOST 0.0.0.0
brew services restart ollama
lsof -nP -iTCP:11434 -sTCP:LISTEN      # 應變成 *:11434
ipconfig getifaddr en0                 # 這台機器的區網 IP
curl http://<區網IP>:11434/api/version  # 從另一台機器測
```

`launchctl setenv` 在登出後失效；要永久生效，把它放進一個 LaunchAgent，或改用 cask 版的 Ollama App（它讀 `launchctl setenv` 與 `~/.zshrc` 以外的設定方式相同）。恢復預設：`launchctl unsetenv OLLAMA_HOST && brew services restart ollama`。

搭配 `OLLAMA_ORIGINS` 控制瀏覽器跨來源請求；macOS 防火牆若開著，第一次會跳出是否允許 `ollama` 接受連線。

> **狀態：未驗證。** 本章撰寫時背景正在下載 Nemotron，重啟服務會中斷下載，所以還沒實測。驗證後會補上實際輸出。

Docker 容器要連主機的 Ollama **不用**開放區網：用 `http://host.docker.internal:11434` 即可（第十六章 Open WebUI 的做法）。

---

## 5-4 調整設定

所有伺服器端設定都是環境變數（完整清單：`ollama serve --help`）。本機 Homebrew 服務目前生效的設定可以從 log 的 `server config` 行看到：

```
OLLAMA_CONTEXT_LENGTH:0  OLLAMA_FLASH_ATTENTION:true  OLLAMA_KV_CACHE_TYPE:q8_0  OLLAMA_KEEP_ALIVE:5m0s
OLLAMA_MAX_LOADED_MODELS:0  OLLAMA_NUM_PARALLEL:1  OLLAMA_MAX_QUEUE:512  OLLAMA_MODELS:/Users/rexwang/.ollama/models
```

### 5-4-1 context 長度

四個層級，後者覆蓋前者：

| 層級 | 設法 | 本機實測 |
|---|---|---|
| 伺服器預設 | `OLLAMA_CONTEXT_LENGTH`；沒設時依 GPU 記憶體自動選 4K / 32K / 256K | log：`vram-based default context ... default_num_ctx=262144` |
| 模型 Modelfile | `PARAMETER num_ctx 32768` | `coder` 模型 `ollama ps` CONTEXT = 32768 |
| 互動模式 | `/set parameter num_ctx 32768` | — |
| 單一請求 | `"options": {"num_ctx": 8192}` | `ollama ps` CONTEXT 從 32768 變 8192，SIZE 從 602 MB 降到 391 MB |

```sh
$ curl -s localhost:11434/api/generate -d '{"model":"hf.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF:Q4_K_M","prompt":"hi","stream":false,"options":{"num_ctx":8192}}'
$ ollama ps
NAME                                            SIZE      PROCESSOR    CONTEXT    RUNNER
hf.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF:Q4_K_M    391 MB    100% GPU     8192       llamacpp
```

GGUF 模型的 CONTEXT 預設是 32768（llama.cpp runner 的上限邏輯），MLX 模型直接用模型原生的 262144。要給 Agent 工具用時至少 64K（第十八章 Hermes 的要求），本機主力模型原生就是 256K，不用調。

### 5-4-2 flash attention 與 KV 量化

Homebrew 的 formula 已經替服務設好 `OLLAMA_FLASH_ATTENTION=1` 和 `OLLAMA_KV_CACHE_TYPE=q8_0`（5-1-1 的 plist），伺服器 log 也確認生效。意義：

- **flash attention**：注意力計算更省記憶體、長 context 更快。
- **KV cache q8_0**：把 KV cache 從 f16 壓成 8-bit，長 context 時快取記憶體約減半，品質幾乎不變。選項：`f16`（預設）、`q8_0`、`q4_0`。

這兩個變數作用在 llama.cpp runner（GGUF 模型）。MLX runner 是否採用同一組設定，Ollama 文件沒有說明，本機也沒有辦法從 log 區分，**此點未驗證**。從 `ollama ps` 看，qwen3.6（MLX）載入 256K context 時 SIZE 為 38–40 GB，和檔案大小差不多，表示 KV cache 的初始配置很小、是按需成長的。

### 5-4-3 常駐與釋放

模型用完預設 **5 分鐘**後卸載（`OLLAMA_KEEP_ALIVE=5m`）。三種改法都實測過：

```sh
# 請求層級：keep_alive 可以是 "10m"、-1（永久）、0（回應完立刻卸載）
curl -s localhost:11434/api/generate -d '{"model":"...","prompt":"hi","stream":false,"keep_alive":-1}'
$ ollama ps
...    UNTIL
...    Forever

curl -s localhost:11434/api/generate -d '{"model":"...","prompt":"hi","stream":false,"keep_alive":0}'
$ ollama ps
(空，已卸載)

# CLI 層級
ollama run <model> --keepalive 1h "hi"     # UNTIL 變成 59 minutes from now

# 手動立刻卸載
ollama stop <model>
```

伺服器層級：`OLLAMA_KEEP_ALIVE=-1` 讓所有模型常駐（設法同 5-3-3，重啟服務後生效）。

建議：主力模型載入要 4.6 秒，日常開發設 `-1` 或 `1h` 省掉每次等待；要跑其他吃記憶體的工作時用 `ollama stop` 釋放 38 GB。

---

## 5-5 Modelfile 與匯入

### 5-5-1 Modelfile

[`examples/ch05/Modelfile.coder`](../examples/ch05/Modelfile.coder)：以主力模型為基底，固定 system prompt、較小 context、較低溫度。

```dockerfile
FROM qwen3.6:35b-a3b-coding-mxfp8
SYSTEM """你是資深軟體工程師。回答以程式碼為主，說明放在程式碼之後，使用繁體中文。
不確定時先問清楚需求，不要猜。"""
PARAMETER num_ctx 32768
PARAMETER temperature 0.3
```

```sh
$ ollama create coder -f examples/ch05/Modelfile.coder
creating new layer sha256:eb4523e5...   # 只多一層幾百 bytes 的參數層
writing manifest
success
$ ollama show coder
  Parameters
    temperature  0.3
    num_ctx      32768
  System
    你是資深軟體工程師。回答以程式碼為主…
$ ollama run coder "寫一個 Python 函式判斷閏年"
```

實測注意事項：

1. **思考模式沒有 Modelfile 參數**。`coder` 繼承了「預設思考」，問閏年先吐出一大段 Thinking。要關：`/set nothink`、API `think:false`，或用 `/save` 把開了 `nothink` 的對話存成模型。
2. `ollama show coder` 的 **Capabilities 區塊是空的**（原模型顯示 completion/vision/tools/thinking），但實測 `/api/chat` 帶 `tools` 給 `coder`，仍正確回傳 `tool_calls`。顯示問題，不影響功能。
3. 衍生模型載入時是**另一份 38 GB**（5-2-3），用完 `ollama stop coder`。
4. 刪除只刪 manifest：`ollama rm coder`。

其他常用指令：`SYSTEM`、`PARAMETER`、`TEMPLATE`、`ADAPTER`（LoRA）、`MESSAGE`（預置對話）、`LICENSE`。

### 5-5-2 匯入 GGUF

**方式一：直接從 Hugging Face 拉**（實測）。格式 `hf.co/<組織>/<repo>:<量化標籤>`，Ollama 會自己找對應的 .gguf 檔：

```sh
$ time ollama pull hf.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF:Q4_K_M
success          # 491 MB，1 分 14 秒
$ ollama run hf.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF:Q4_K_M --verbose "Say hello in Chinese."
你好，有什么我可以帮助你的吗？
eval rate:            199.89 tokens/s
$ ollama ps
NAME                                            SIZE      PROCESSOR    CONTEXT    RUNNER
hf.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF:Q4_K_M    602 MB    100% GPU     32768      llamacpp
```

**方式二：本機 .gguf 檔**（未驗證，但只是把 `FROM` 指到檔案）：

```dockerfile
FROM ./model-Q4_K_M.gguf
```
```sh
ollama create mymodel -f Modelfile
```

`ollama create` 也能直接吃 safetensors 目錄並量化（`--quantize nvfp4` 等，見 `ollama create --help`），本章沒測。

匯入 GGUF 的一個額外好處：llama.cpp runner 支援 `format`（JSON Schema 結構化輸出），MLX 不支援：

```sh
$ curl -s localhost:11434/api/chat -d '{"model":"hf.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF:Q4_K_M", "messages":[...],
   "stream":false, "format":{"type":"object","properties":{"country":{"type":"string"},"population":{"type":"integer"}},"required":["country","population"]}}'
{"country": "Taipei", "population": 9000000}     # 格式正確（0.5B 模型答案本身不準，是模型能力問題）
```

---

## 5-6 已知問題

### 5-6-1 structured output is unavailable

這台機器上最常撞到的錯誤：**MLX runner 不支援結構化輸出**。任何帶 `format` 的請求（`"json"` 或 JSON Schema）都會失敗：

```sh
$ curl -s localhost:11434/api/generate -d '{"model":"qwen3.6:35b-a3b-coding-mxfp8","prompt":"...","format":"json","stream":false}'
{"error":"structured output is unavailable"}
```

log 的原因：

```
level=WARN source=grammar.go:74 msg="Structured output is unavailable" error="xgrammar library not found at /opt/homebrew/Cellar/ollama/0.40.13/libexec/lib/ollama/mlx_metal_v3/libollama_xgrammar.dylib"
```

Homebrew 的 0.40.13 沒有附 MLX 用的 xgrammar 函式庫。三個做法：

| 做法 | 適用 |
|---|---|
| 提示詞要求 JSON + 程式端用 pydantic 驗證、失敗重試（[`06_json_output.py`](../examples/ch05/06_json_output.py)，實測一次就過） | 最通用 |
| 改用 GGUF 標籤（例如 `qwen3.6:35b-a3b-q8_0`，39 GB），走 llama.cpp runner | 需要嚴格 schema 時 |
| 用工具呼叫代替：定義一個 function，參數就是你要的 schema，模型回 `tool_calls.arguments` 已是 JSON | Agent 情境 |

```
$ python 06_json_output.py
name='Taipei' country='Taiwan' population=2500000
```

### 5-6-2 記憶體回報不準

macOS 統一記憶體沒有「專屬 / 共用 GPU 記憶體」的區分，本機實測三個模型同時載入時，`ollama ps` 的 SIZE 與行程的實際 physical footprint 很接近：

| 模型 | 檔案大小 | `ollama ps` SIZE | 行程 `footprint` |
|---|---|---|---|
| qwen3.6 mxfp8（256K ctx） | 38 GB | 39 GB | 37 GB（峰值 38） |
| coder（同權重，32K ctx） | 38 GB | 38 GB | 36 GB（峰值 37） |
| Qwen2.5-0.5B GGUF（32K ctx） | 491 MB | 602 MB | 293 MB（峰值 425） |

```sh
ollama ps
ps -axo rss,pid,command | grep "ollama runner"
footprint -p <runner pid>        # phys_footprint 才是 macOS 真正計帳的數字
```

真正會讓數字「看起來不準」的地方：

1. **SIZE 會隨 context 變動**：同一個 GGUF 模型 `num_ctx` 8192 時 391 MB，32768 時 602 MB。這是 KV cache 的預留量，不是模型變了。
2. **MLX 模型的 KV cache 是按需成長**：`ollama ps` 的 39 GB 只反映目前狀態，256K context 真的塞滿時會再長數 GB。log 的 `msg=memory peak=... held=...` 每次請求都會印目前峰值。
3. **`ollama ps` 的 SIZE 單位是 GB（10^9），log 用 GiB（2^30）**，38 GB ≈ 35.7 GiB。
4. 活動監視器看的是整個系統，Ollama 之外的 GPU 用量（瀏覽器、IDE）也算在 wired 記憶體裡，接近 107.5 GiB 上限時會開始把模型層放到 CPU（`PROCESSOR` 不再是 100% GPU）。

### 5-6-3 MLX runner 卡在 Stopping...（本機實際遇到）

**現象**：Open WebUI 對 `qwen3.6:35b-a3b-coding-mxfp8` 送出第一個 RAG 請求（思考模式開著、串流）後一直沒有回應；之後所有排隊的請求都被卡住，`ollama ps` 的 `UNTIL` 欄顯示 `Stopping...` 超過 10 分鐘不變，`ollama stop` 也無效。同一時間另一個只做一句話問答的 Hermes Agent 請求花了 7 分 17 秒才回來（正常情況 7 秒）。

```
$ ollama ps
NAME                            SIZE     PROCESSOR    CONTEXT    RUNNER    UNTIL
qwen3.6:35b-a3b-coding-mxfp8    38 GB    100% GPU     262144     mlx       Stopping...
```

**解法**：直接砍掉 runner 子行程，Ollama 主程式（`ollama serve`）不用重啟，下一個請求會重新載入模型（約 5 秒）。

```sh
ps -axo pid,command | grep "ollama runner"        # 找到 runner 的 pid
kill -9 <runner pid>
ollama ps                                          # 應該變成空的
```

**預防**：對 MLX 模型的長時間串流請求，呼叫端要設合理的 timeout；用 Open WebUI 時把模型的進階參數設成 `"think": false`（第十六章 16-3-2）。這台機器上目前只重現過一次，`ollama serve` 的 log 沒有錯誤訊息。

---

## 5-7 本章小結

| 主題 | 這台機器的結論 |
|---|---|
| 安裝 | `brew install ollama` + `brew services start ollama`，arm64 原生，GPU 可用 107.5 GiB |
| 主力模型 | `qwen3.6:35b-a3b-coding-mxfp8`，MoE 36B/3B 啟用，MLX，38 GB，約 120 tok/s，256K context |
| API | 原生 `/api/*`；OpenAI 相容 `/v1`（關思考要用 `reasoning_effort:"none"`） |
| 多模型 | 可同時載入；衍生模型會再佔一份記憶體 |
| 設定 | 環境變數經 `launchctl setenv` + `brew services restart`；`keep_alive` 控制常駐 |
| 匯入 | `ollama pull hf.co/<repo>:<quant>` 最快 |
| 限制 | MLX 不支援 `format`；Modelfile 無法關思考；MLX runner 曾卡在 Stopping...（kill -9 runner 解決） |
| 待補 | Nemotron 3.5 Super 執行結果、`OLLAMA_HOST` 區網開放的實測 |
