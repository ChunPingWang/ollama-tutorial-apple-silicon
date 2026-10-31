# 附錄 A 模型調優參數指南

這一章把前面各章用到的參數集中整理，目標是讓初學者知道：**有哪些東西可以調、每個參數在管什麼、調了會發生什麼事、在這台機器上建議設多少**。所有輸出都是 2026-10-31 在本機實際執行的結果；為了不佔用正在工作的主力模型，採樣參數的示範用 491 MB 的小模型 `hf.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF:Q4_K_M`，效果和大模型相同，只是回答品質比較差。

## A-1 參數分三層，後者覆蓋前者

| 層級 | 設在哪裡 | 影響範圍 | 什麼時候改 |
|---|---|---|---|
| 1. 伺服器環境變數 `OLLAMA_*` | `launchctl setenv` + `brew services restart ollama`（1-3-3） | 這台機器上所有模型、所有程式 | 記憶體、連接埠、常駐時間等「機器層面」的事 |
| 2. 模型參數（Modelfile `PARAMETER`） | `ollama create` 建衍生模型（1-5-1） | 這一個模型名稱，所有程式 | 想讓某個模型「預設就是這樣」，例如固定 32K context、固定低溫度 |
| 3. 單一請求 `options` | REST `/api/*` 的 `options`、Python `ollama.chat(options=...)`、CLI `/set parameter` | 只有這一次請求 | 做實驗、不同任務用不同設定 |

優先順序：**請求 > Modelfile > 模型內建預設 > 伺服器環境變數**。1-4-1 的 context 實驗就是這個順序：伺服器預設 262144，Modelfile 設 32768 就變 32768，單一請求送 8192 就變 8192。

模型自己也帶一組預設值，用 `ollama show <模型> --parameters` 看。主力模型的內建值：

```sh
$ ollama show qwen3.6:35b-a3b-coding-mxfp8 --parameters
min_p                          0
presence_penalty               0
repeat_penalty                 1
temperature                    0.6
top_k                          20
top_p                          0.95
```

`nemotron-3.5-super` 和匯入的 GGUF 小模型這個指令印出空白，表示作者沒有帶預設值，會用 Ollama 的程式預設（依 Ollama 文件：temperature 0.8、top_k 40、top_p 0.9、repeat_penalty 1.1，本機未另行驗證）。**先查這個，再決定要不要改。**

## A-2 先弄懂三個名詞

- **token**：模型處理文字的最小單位。中文大約 1 個字 1 到 2 個 token，英文大約 0.75 個單字 1 個 token。`ollama run --verbose` 印的 `eval count` 就是這次回答的 token 數。
- **context（上下文窗）**：模型一次能「看見」的 token 總數，包含 system prompt、對話歷史、工具定義、文件內容、以及它正在產生的回答。超過就會被截掉最舊的部分。對應參數 `num_ctx`。
- **KV cache**：模型為 context 裡每個 token 存的中間結果，是記憶體的主要變數。context 越長、實際塞進去的內容越多，這塊就越大。`ollama ps` 的 SIZE 欄位 = 模型權重 + 目前用到的 KV cache。

一個今天在本機看到的實例：同一個 `qwen3.6:35b-a3b-coding-mxfp8`，

| 情境 | `ollama ps` CONTEXT | `ollama ps` SIZE |
|---|---|---|
| 一般問答，context 用預設 262144，但每次只送幾千 token | 262144 | 38–40 GB |
| 另一個 Agent 程式指定 `num_ctx` 32768，每次送約 26K token 的長 prompt | 32768 | 51 GB |

context 上限反而小的那一個比較吃記憶體，因為 **SIZE 看的是實際塞進快取的量，不是上限**。所以判斷記憶體夠不夠，要看你真的會送多長的內容，不是只看 `num_ctx`。

## A-3 影響記憶體與速度的參數

這一組決定「跑得動嗎、跑多快、能同時開幾個」。

### `num_ctx`：context 長度

| | 說明 |
|---|---|
| 是什麼 | 這次請求允許的 context 上限（token） |
| 預設 | MLX 模型用模型原生值（qwen3.6 = 262144）；GGUF 模型 32768；或由 `OLLAMA_CONTEXT_LENGTH` 統一指定 |
| 調大 | 能塞更長的文件、更多輪對話、更多工具定義；KV cache 上限變大 |
| 調小 | 省記憶體、載入快一點；內容超過時會被靜默截斷，Agent 會「忘記」前面的工具結果，這是最常見的奇怪錯誤來源 |
| 本機建議 | 主力模型維持原生 256K 不用動。給 Hermes 等 Agent 用的模型至少 64K（3-7-2 的硬性下限）。只拿來做短問答或分類的小模型可以設 4096–8192 |
| 驗證 | 1-4-1 的實驗；本章 A-6 的 `/v1` 測試 |

實測：同一個小模型 `num_ctx` 4096 時 SIZE 315 MB，8192 時 391 MB，32768 時 602 MB。

### `keep_alive` / `OLLAMA_KEEP_ALIVE`：模型在記憶體裡停多久

| | 說明 |
|---|---|
| 是什麼 | 回答完後模型繼續留在記憶體的時間 |
| 預設 | 5 分鐘 |
| 值 | `"10m"`、`"1h"`、`-1`（永久）、`0`（回答完立刻卸載） |
| 調長 | 省掉每次 4.6 秒（主力模型）到數十秒（Nemotron）的載入時間 |
| 調短 | 把記憶體還給 Docker、IDE 或另一個模型 |
| 本機建議 | 日常開發對主力模型設 `-1` 或 `1h`；要跑大模型前先 `ollama stop` 小的 |
| 驗證 | 1-4-3 三種設法都有輸出 |

### `OLLAMA_MAX_LOADED_MODELS`、`OLLAMA_NUM_PARALLEL`：同時幾個模型、幾個請求

| | 說明 |
|---|---|
| `OLLAMA_MAX_LOADED_MODELS` | 同時留在記憶體的模型數。預設 0 = 自動（單 GPU 為 3）。記憶體不夠時卸載最久沒用的。本機實測三個模型同時在 GPU（1-2-3） |
| `OLLAMA_NUM_PARALLEL` | 同一個模型同時處理幾個請求。本機預設 1，第二個請求會排隊。調成 2 或 4 時 KV cache 會按倍數預留，每個請求實際可用的 context 也會被均分（Ollama 文件說明，本機未調整） |
| 本機建議 | 兩者維持預設。本機 107.5 GiB 的 GPU 記憶體裝一個 84 GiB 的 Nemotron 後就裝不下第二個大模型，Ollama 會等忙碌中的模型閒置才卸載它，所以**大模型和忙碌的 Agent 不能同時用**（今天實際發生：Nemotron 的載入請求排隊超過兩小時） |

### `OLLAMA_FLASH_ATTENTION`、`OLLAMA_KV_CACHE_TYPE`：長 context 的記憶體

Homebrew 已經替服務設好 `OLLAMA_FLASH_ATTENTION=1`、`OLLAMA_KV_CACHE_TYPE=q8_0`（1-4-2），不需要再改。KV cache 可選 `f16`（最精確）、`q8_0`（約省一半，品質幾乎不變）、`q4_0`（再省一半，長文件任務品質會掉）。要改回 f16 只有在懷疑長 context 回答品質變差時才需要。這組設定作用在 llama.cpp runner，MLX runner 是否採用**未驗證**。

### `num_predict`：最多回答幾個 token

| | 說明 |
|---|---|
| 是什麼 | 回答的 token 上限。`/v1` 端點叫 `max_tokens` |
| 預設 | -1 = 不限制（直到模型自己停或 context 滿） |
| 用途 | 防止模型講不停、控制回應時間；RAG 的 rerank 只要回「是 / 否」時設成 4（2-3 的 `rag.py`） |
| 驗證 | 下面的輸出 |

```sh
$ curl -s localhost:11434/api/generate -d '{"model":"hf.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF:Q4_K_M",
  "prompt":"請詳細介紹 Python 的歷史。","stream":false,"options":{"num_predict":8}}'
response: 'Python 作為一種超級簡易'   done_reason: length   eval_count: 8
```

`done_reason` 是 `length` 就表示被上限截斷了，程式裡可以用它判斷要不要續問。

### 量化標籤：載入前就決定的大小與速度

這不是執行期參數，但它是最大的「調優」：同一個模型選 4-bit 標籤只要一半記憶體，8-bit 品質接近原始。選法見 1-2-2。經驗法則：

1. 記憶體夠就用 8-bit（`mxfp8` / `q8_0`）。
2. MoE（`a3b`）比同大小的 Dense 快很多，因為每個 token 只算一小部分參數。
3. safetensors 走 MLX（快），GGUF 走 llama.cpp（功能完整，有 structured output）。

### 其他看得到但本機不用動的

| 參數 | 說明 |
|---|---|
| `num_gpu` | 放到 GPU 的層數。Apple Silicon 統一記憶體，預設全部放 GPU，`ollama ps` 顯示 100% GPU。MLX runner 是否理會此參數**未驗證** |
| `num_thread` | CPU 執行緒數，只有模型落到 CPU 時才有意義。本機沒有這種情況 |
| `num_batch` | prompt 處理的批次大小，影響長 prompt 的處理速度與暫存記憶體。本機未調整 |
| `OLLAMA_GPU_OVERHEAD`、`LLAMA_ARG_FIT*` | 多 GPU 或要手動留 VRAM 時用。本機單 GPU，不需要 |

## A-4 影響回答內容的參數（採樣參數）

模型每產生一個 token，其實是算出所有候選 token 的機率，再「抽」一個。這組參數控制怎麼抽。它們不影響記憶體，隨時可以改。

### `temperature`：隨機程度

| 值 | 效果 | 適合 |
|---|---|---|
| 0 | 幾乎每次都選機率最高的那個 token | 寫程式、工具呼叫、抽取欄位、分類、RAG 回答 |
| 0.3–0.6 | 穩定但不死板（qwen3.6 的內建值 0.6） | 一般問答、摘要 |
| 0.8–1.0 | 多樣（Ollama 程式預設 0.8） | 腦力激盪、聊天 |
| > 1.2 | 常常偏題、出現亂碼或換語言 | 很少有用 |

實測同一題問三次：

```
temperature 0
台北，一座充满历史与现代气息的城市，以其独特的建筑风格……成为中国大陆的“硅谷”之一。
台北，一座充满历史与现代气息的城市，以其独特的建筑风格……成为中国大陆的“国际大都会”之一。
台北，一座充满历史与现代气息的城市，以其独特的建筑风格……成为中国大陆的“国际大都会”之一。

temperature 1.5
台北是一座充满历史、文化和现代化融合的城市，以其现代化的现代气息……
台北是台湾省首府，世界文化遗产，海峡两岸交流频繁的城市……
台北，一 nationwide city known as the "metropolis of all metropolises" and "city of
```

兩個觀察：temperature 0 三次幾乎一樣，但第一次最後幾個字仍不同，**temperature 0 不保證逐字相同**，要可重現請加 `seed`；temperature 1.5 第三次直接混進英文。（小模型用簡體回答是它本身的訓練偏向，和參數無關。）

### `seed`：固定隨機種子

同一個 `seed` 加同一組參數與 prompt，會得到同樣的答案。做測試、比較兩個 prompt 版本時用。

```
seed 42, temperature 0.8，連問兩次「寫一個三個字的中文名字。」
晨曦
晨曦
```

### `top_p`、`top_k`、`min_p`：限制候選範圍

這三個和 temperature 一起決定抽樣範圍，初學者通常不用動，知道意思就好：

| 參數 | 意思 | qwen3.6 內建 | Ollama 程式預設 |
|---|---|---|---|
| `top_k` | 只從機率最高的前 k 個 token 裡抽 | 20 | 40 |
| `top_p` | 只從累積機率達到 p 的那群 token 裡抽（0.95 = 丟掉尾端 5% 的冷門選項） | 0.95 | 0.9 |
| `min_p` | 機率低於「最高機率 × min_p」的 token 直接排除 | 0 | 0 |

要讓回答更保守：調低 `top_p`（0.8）或 `top_k`（10）。要更有變化：調高。這些值和 temperature 是乘法關係，一次只動一個，不然看不出是誰造成的。

### `repeat_penalty`、`presence_penalty`、`frequency_penalty`：防止重複

| 參數 | 意思 | 預設 |
|---|---|---|
| `repeat_penalty` | 已出現過的 token 機率乘以懲罰，> 1 越不想重複 | qwen3.6 內建 1（不懲罰）；Ollama 程式預設 1.1 |
| `presence_penalty` | 出現過就減分，不看次數（OpenAI 風格） | 0 |
| `frequency_penalty` | 出現越多次減越多分 | 0 |

調太高會讓模型連該重複的字（程式碼裡的變數名、標點）都不敢用。實測叫小模型「重複說十次：好」：

```
repeat_penalty 1.0 → 好的，我再重複說十次：好
repeat_penalty 1.5 → 好的，我再繫合一次：\n\n你好！有什么我可以帮你的好嗎？
```

1.5 時連「重複」兩個字都被扭成「繫合」。寫程式的任務建議保持 1.0，看到模型跳針（同一句話一直重複）才調到 1.05–1.15。

### `stop`：遇到什麼字就停

一串字串，模型輸出到任何一個就結束，而且停止字串本身不會出現在回答裡。用途：只要第一句、只要第一行程式、或在自己設計的對話格式裡擋住模型「幫使用者接話」。

```sh
"options":{"stop":["。"]}
response: '1. Python 是一種流行的高级編程語言，創立於20世纪70年代'   done_reason: stop
```

### `think`：要不要先推理

這不是 `options`，是請求的最上層欄位（1-3-1）。

| 值 | 意思 |
|---|---|
| `true` / `false` | 開 / 關思考。關掉後回答快很多，簡單任務品質差不多 |
| `"low"` / `"medium"` / `"high"` | 思考預算等級，只有模型宣告支援才有效。`ollama show` 的 Capabilities 會列 `levels` |

本機兩個模型的差異：

```
qwen3.6:35b-a3b-coding-mxfp8   thinking levels: false, true          default true
nemotron-3.5-super             thinking levels: false, true, medium  default true
```

所以 qwen3.6 只能開關，`--think high` 沒有作用；Nemotron 多一個 `medium`。CLI 用 `ollama run <模型> --think=false`，`/v1` 端點要用 `reasoning_effort: "none"`（1-3-2）。Modelfile 無法關思考（1-5-1），要固定關閉只能在程式裡每次送。

### 常見任務的建議組合

| 任務 | temperature | 其他 | 原因 |
|---|---|---|---|
| 寫程式、修 bug | 0–0.2 | `think` 視難度；`repeat_penalty` 1.0 | 要的是正確，不是創意 |
| 工具呼叫 / Agent | 0–0.3 | `num_ctx` ≥ 64K | 參數名稱、JSON 格式不能有變化 |
| RAG 問答 | 0 | `num_predict` 設上限；rerank 用 `num_predict` 4 | 答案只能來自文件 |
| 抽取欄位、分類 | 0 | `stop` 或 `format`（GGUF 模型） | 要可機器解析 |
| 摘要、翻譯 | 0.3 | — | 穩定但不逐字抄 |
| 文案、腦力激盪 | 0.9–1.1 | `seed` 不固定 | 要變化 |
| 回歸測試、比較 prompt | 0 | 固定 `seed` | 要可重現 |

## A-5 伺服器環境變數總表

`ollama serve --help` 列出的全部變數，加上本機目前的值（取自伺服器 log 的 `server config` 行，1-4）：

| 變數 | 功能 | 本機目前值 | 建議 |
|---|---|---|---|
| `OLLAMA_HOST` | 監聽位址與連接埠 | `127.0.0.1:11434` | 只在要給區網其他機器用時改 `0.0.0.0`（1-3-3） |
| `OLLAMA_MODELS` | 模型檔目錄 | `~/.ollama/models` | 磁碟不夠時指到外接碟（1-1-3） |
| `OLLAMA_CONTEXT_LENGTH` | 所有模型的預設 context | `0`（自動，本機得 262144） | 維持。要省記憶體可設 `65536` |
| `OLLAMA_KEEP_ALIVE` | 預設常駐時間 | `5m` | 日常開發可設 `1h` 或 `-1` |
| `OLLAMA_MAX_LOADED_MODELS` | 同時載入的模型數 | `0`（自動，單 GPU 3 個） | 維持 |
| `OLLAMA_NUM_PARALLEL` | 同一模型平行請求數 | `1` | 多人共用時才調 2–4 |
| `OLLAMA_MAX_QUEUE` | 排隊請求上限 | `512` | 維持 |
| `OLLAMA_FLASH_ATTENTION` | flash attention | `true`（Homebrew 預設） | 維持 |
| `OLLAMA_KV_CACHE_TYPE` | KV cache 精度 | `q8_0`（Homebrew 預設） | 維持；懷疑長文件品質時試 `f16` |
| `OLLAMA_ORIGINS` | 允許的瀏覽器來源 | 未設 | 自己寫網頁前端直接打 Ollama 時才需要 |
| `OLLAMA_NO_CLOUD` | 關閉雲端功能 | 未設 | 完全離線環境可設 `1` |
| `OLLAMA_NOPRUNE` | 啟動時不清理未用的 blob | 未設 | 維持 |
| `OLLAMA_LOAD_TIMEOUT` | 載入卡住多久放棄 | `5m` | 載入 80 GB 以上模型若超時可拉長 |
| `OLLAMA_DEBUG` | 詳細 log | 未設 | 除錯時設 `1`，看完記得關 |
| `OLLAMA_MAX_TRANSFER_STREAMS` | 下載 safetensors 的平行連線數 | `4` | 下載慢且頻寬夠時可調高 |
| `OLLAMA_SCHED_SPREAD`、`OLLAMA_GPU_OVERHEAD`、`OLLAMA_IGPU_ENABLE`、`OLLAMA_LLM_LIBRARY`、`LLAMA_ARG_FIT*` | 多 GPU、特殊硬體 | 未設 | 本機單 GPU，不需要 |

修改方式（Homebrew 背景服務）：

```sh
launchctl setenv OLLAMA_KEEP_ALIVE 1h     # 先設到 launchd 環境
brew services restart ollama              # 服務重啟後才讀到
grep "server config" /opt/homebrew/var/log/ollama.log | tail -1   # 確認生效
```

`launchctl setenv` 登出後失效，要永久生效見 1-3-3 的說明。

## A-6 在各種工具裡怎麼設

同一個參數，不同入口的寫法：

| 入口 | 寫法 | 備註 |
|---|---|---|
| CLI 互動模式 | `/set parameter temperature 0`、`/set parameter num_ctx 32768` | 只在這個對話有效 |
| CLI 一次性 | `ollama run <模型> --think=false --keepalive 1h --verbose "問題"` | `--format json` 只對 GGUF 模型有效（1-6-1） |
| 原生 REST `/api/generate`、`/api/chat` | `"options": {"temperature": 0, "num_ctx": 8192, "num_predict": 200, "seed": 42, "stop": ["。"]}`；`"think": false`、`"keep_alive": -1` 放最上層 | 功能最完整 |
| Python `ollama` 套件 | `ollama.chat(model=..., messages=..., think=False, options={"temperature": 0, "num_predict": 4})` | 2-3 的 `rag.py` 就是這樣寫 |
| OpenAI 相容 `/v1` | `temperature`、`top_p`、`max_tokens`、`seed`、`stop`、`presence_penalty`、`frequency_penalty`、`reasoning_effort` 用 OpenAI 的欄位名 | **不接受 `options`、不能改 `num_ctx`**（實測見下） |
| Modelfile | `PARAMETER temperature 0.3`、`PARAMETER num_ctx 32768`、`PARAMETER stop "<|im_end|>"` | 建成新模型名稱後對所有程式生效；會多佔一份記憶體（1-5-1） |
| Hermes Agent | `hermes config set model.ollama_num_ctx 65536`；`--reasoning none` | Hermes 會自己送 `options.num_ctx`（3-7-2、3-8-2） |
| Open WebUI | 模型設定裡的 Advanced Params，或 API 的 `params` | 2-4-1 用 `params.think=false` |

`/v1` 端點實測（小模型）：

```
max_tokens 8               → finish_reason: length, completion_tokens: 8      （對應 num_predict）
seed 7 + temperature 0.8 ×2 → 李明思 / 李明思                                   （可重現）
options.num_ctx 4096       → 請求成功，但 ollama ps CONTEXT 仍是 32768         （被忽略）
/api/generate options.num_ctx 4096 → ollama ps CONTEXT 4096, SIZE 315 MB     （原生 API 有效）
```

結論：用 OpenAI SDK 的程式（Hermes、Open WebUI、AnythingLLM 等）**改不了 context**，要改 context 只能在 Modelfile 或伺服器環境變數那兩層做。這就是第三章 Hermes 要特別處理 `num_ctx` 的原因。

## A-7 初學者的調參流程

1. **先用預設跑一次**，開 `--verbose` 看速度，開另一個終端看 `ollama ps`。沒問題就不要調。
2. **記憶體不夠或載入太慢** → 先換小一號的量化標籤（A-3 量化），再考慮 `num_ctx`。不要一開始就調 KV cache 精度。
3. **Agent 忘記前面的事、工具呼叫莫名失敗** → 看 context 是否被截斷：`ollama ps` 的 CONTEXT 夠不夠、程式送的內容多長。先把 `num_ctx` 拉到 64K 以上。
4. **每次呼叫都等載入** → `keep_alive` 設 `-1` 或 `1h`。
5. **回答不穩定、格式亂** → `temperature` 降到 0，必要時固定 `seed`、加 `stop`，GGUF 模型可以用 `format`。
6. **回答太死板、沒變化** → `temperature` 升到 0.8–1.0，順便確認不是在跑應該穩定的任務。
7. **模型跳針重複** → `repeat_penalty` 1.05–1.15，一次調一點。
8. **一次只改一個參數**，改完用同一題、同一個 `seed` 比較。把有效的組合寫進 Modelfile，之後所有程式一起受惠。

## A-8 本章小結

| 想調的事 | 參數 | 層級 |
|---|---|---|
| 記憶體與能塞多少內容 | `num_ctx`、量化標籤、`OLLAMA_KV_CACHE_TYPE` | 請求 / Modelfile / 伺服器 |
| 載入等待 | `keep_alive`、`OLLAMA_KEEP_ALIVE` | 請求 / 伺服器 |
| 同時幾個模型、幾個請求 | `OLLAMA_MAX_LOADED_MODELS`、`OLLAMA_NUM_PARALLEL` | 伺服器 |
| 回答穩不穩 | `temperature`、`seed`、`top_p`、`top_k` | 請求 / Modelfile |
| 回答多長、何時停 | `num_predict`（`max_tokens`）、`stop` | 請求 / Modelfile |
| 會不會跳針 | `repeat_penalty`、`presence_penalty` | 請求 / Modelfile |
| 先想再答 | `think`（`reasoning_effort`） | 請求 |
| 給誰連 | `OLLAMA_HOST`、`OLLAMA_ORIGINS` | 伺服器 |

本機主力模型 `qwen3.6:35b-a3b-coding-mxfp8` 的建議：context 維持 256K、`keep_alive -1`、寫程式與 Agent 任務 `temperature 0–0.3`、其餘沿用模型內建值。
