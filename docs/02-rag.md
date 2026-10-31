# 第二章：RAG

> 實測環境：Apple M5 Max / 128 GB / macOS 27.2 / Ollama 0.40.13（brew service）。
> 本章所有指令與輸出都在這台機器上實際執行過；沒做到的會標「未驗證」或「本機略過」。
> 範例程式在 `examples/ch02/`，用 `python3 -m venv .venv && source .venv/bin/activate && pip install -r examples/ch02/requirements.txt` 準備環境。

## 2-1 RAG 原理

### 2-1-1 檢索與生成

RAG（Retrieval-Augmented Generation）把「回答問題」拆成兩步：

| 步驟 | 做什麼 | 本章用的工具 |
|---|---|---|
| 檢索 (Retrieval) | 從自己的文件裡找出和問題最相關的幾段 | `qwen3-embedding:0.6b` + sqlite-vec / Qdrant |
| 生成 (Generation) | 把找到的段落連同問題交給 LLM，要它「只根據資料回答」 | `qwen3.6:35b-a3b-coding-mxfp8` |

為什麼不直接把整份文件塞進 prompt？qwen3.6 的 context 有 256K，本章 4 份文件只有 4,785 字元，塞得下。但文件一多就塞不下，而且每次都要重算整份 prompt。實測 `rag.py` 一次只送 3 段（約 320 到 415 個 prompt tokens），生成 0.7 秒就回答完。

RAG 的另一個好處是**可追溯**：回答後面標 `[1]` 這類編號，可以回頭查是哪一段文件說的。資料裡沒有的問題，模型會回「不知道」（2-4-1 有實測）。

### 2-1-2 embedding

embedding 模型把一段文字變成一個固定長度的向量，語意接近的文字向量方向也接近。比較兩個向量用餘弦相似度（cosine similarity），1 表示完全相同方向，0 表示無關。

實測 `examples/ch02/embed_demo.py`，查詢句是「模型檔案存放的目錄在哪裡？」：

| 候選句 | qwen3-embedding:0.6b | embeddinggemma |
|---|---|---|
| Ollama 的模型放在 ~/.ollama/models | **0.572** | **0.667** |
| Docker Desktop 需要 sudo 密碼才能安裝 | 0.375 | 0.273 |
| 今天晚餐想吃牛肉麵 | 0.263 | 0.211 |

兩個模型都把正確答案排第一，而且查詢句和答案句沒有任何共同關鍵字（「存放的目錄」對「放在 ~/.ollama/models」），這是關鍵字搜尋做不到的。絕對分數不能跨模型比較，只看同一模型內的排序。

## 2-2 建立索引

### 2-2-1 切分文件

文件要先切成「塊」（chunk），每塊各算一個向量。塊太大，一塊裡混了多個主題，向量會模糊；塊太小，上下文不夠，模型答不出來。切分沒有放諸四海皆準的「最佳」做法，要看文件長什麼樣子、問題長什麼樣子，再用一組已知答案的問題去量。

#### 常見的切分方法論

| 方法 | 做法 | 適用情境 | 優點 | 缺點 | 本章 |
|---|---|---|---|---|---|
| **固定長度**（fixed-size） | 每 N 個字元或 token 一塊，相鄰兩塊重疊 10–20% | 沒有結構的純文字、逐字稿、log | 最簡單；任何文字都能切；塊長度可預測 | 句子和段落會被切斷，要靠 overlap 補；塊和主題無關 | `fixed_size`，300 字元 / 重疊 60 |
| **句子 / 段落** | 以句號、換行、空白行為界，一句或一段一塊 | 短問答、FAQ、條列式文件 | 不會切斷句子 | 長度落差大；一段話太長時還是要再切 | 包含在遞迴切分的第 2、3 層 |
| **遞迴切分**（recursive） | 先用最粗的分隔符（空白行）切，太長再用換行、句號、逗號往下切，最後把相鄰小片段合併到接近目標長度 | 通用文字，結構不明顯但有段落。LangChain 的預設做法 | 盡量保留段落與句子邊界，長度又接近固定 | 分隔符要配合語言（中文是全形句號）；標題行可能被黏到前一塊（實測遇到） | `recursive`，300 字元 |
| **結構感知**（structure-aware） | 依 Markdown 標題、HTML 標籤、PDF 章節、程式碼的函式或類別切 | 技術文件、手冊、原始碼、網頁 | 一塊就是一個完整主題；標題可以當引用來源；可以把標題補進塊裡強化向量 | 要有結構才行；小節長度不均，超長小節要再做第二層切分 | **`by_heading`（本章採用）** |
| **語意切分**（semantic） | 逐句算 embedding，相鄰句子相似度突然掉下去的地方就是邊界 | 沒有結構但主題會轉換的長文（文章、會議紀錄） | 邊界跟著主題走 | 每句都要算向量，建索引慢；閾值要調；結果不穩定 | 未實作 |
| **父子塊**（parent-child / small-to-big） | 用小塊（句子）做檢索，命中後把它所屬的大塊（整個小節）交給模型 | 問題精確但答案需要前後文 | 檢索準、生成時上下文足 | 索引要存兩層；實作較複雜 | 未實作；AnythingLLM、Open WebUI 也沒有 |
| **上下文補強**（contextual retrieval） | 建索引時先請 LLM 替每一塊寫一句「這段在整份文件裡的位置與主題」，接在塊前面再做向量 | 塊脫離上下文會看不懂的文件（合約、規格書） | 大幅減少「這一段在講誰」的誤檢索 | 每一塊都要跑一次 LLM，建索引成本高 | 未實作；`by_heading` 把標題補進塊裡是它的簡化版 |
| **LLM 切分**（agentic / propositional） | 直接請 LLM 把文件拆成獨立、自足的命題 | 資料量小但品質要求極高 | 每塊都是完整事實 | 最貴、最慢、結果不可重現 | 未實作 |

通用的經驗法則：

1. **文件有結構就先用結構**（標題、段落、函式）；沒有就用遞迴切分。固定長度只在前兩者都不適用時才用。
2. **塊的大小**：embedding 模型的 context 是上限（`qwen3-embedding:0.6b` 是 32768 token），但實務上 200–500 token 最常見。塊小檢索準、塊大生成好，拿不定就用父子塊。
3. **每塊都帶 metadata**（檔名、標題、頁碼），引用與除錯都靠它。
4. **一定要量**：準備 10 到 50 個「我知道答案在哪一段」的問題，比較不同切法的命中率，而不是憑感覺。
5. **overlap** 只對固定長度切分重要，結構感知切分不需要。

#### 本章實作與實測

`examples/ch02/chunk.py` 實作固定長度、遞迴、結構感知三種，對 `examples/ch02/corpus/` 的 4 份 Markdown 文件實測：

```
$ python chunk.py
[heading  ] 16 塊，長度 min 80 / avg 184 / max 335 字元
[fixed    ] 15 塊，長度 min 30 / avg 244 / max 300 字元
[recursive] 14 塊，長度 min 107 / avg 215 / max 298 字元

依標題切的前三塊：
  - 01-本機環境.md › 本機開發環境（80 字元）
  - 01-本機環境.md › zsh 與 Powerlevel10k（258 字元）
  - 01-本機環境.md › Docker Desktop（280 字元）
```

`chunk_compare.py` 用 10 個已知答案位置的問題，對三種切法各建一次向量（`qwen3-embedding:0.6b`）再檢索：

```
$ python chunk_compare.py
切法          塊數   平均字元  平均token  top-1  top-3
heading     16    184       99  10/10  10/10
fixed       15    244      130   9/10  10/10
          第 1 名沒命中（第 2–3 名有）：iTerm2 字型選單找不到 MesloLGS 怎麼辦？
recursive   14    215      114   9/10  10/10
          第 1 名沒命中（第 2–3 名有）：可以同時載入幾個模型？
```

**本章採用 `by_heading`（結構感知切分，每塊前面補上標題）**，理由：

- 語料是 Markdown 技術文件，每個 `##` 小節本來就是一個主題，長度 80 到 335 字元，不需要再切。
- 標題補進塊裡等於免費的上下文補強：「模型存放位置」這四個字讓「~/.ollama/models」那塊更容易被「模型檔放在哪」命中。
- 檢索結果可以直接顯示「檔名 › 小節」，讀者對照原文最方便，後面 2-4 的引用標註就靠它。
- 不需要額外模型、結果可重現，教學時容易解釋。
- 實測在這個語料上 top-1 全中；另外兩種各有一題掉到第 2、3 名。

要誠實說明的限制：語料只有 4 份文件、16 塊，三種方法的 top-3 都是全中，差距只在 top-1 的一題。文件多到上千塊時差距會明顯得多，也更需要 rerank（2-4-2）。另一個實測看到的小陷阱：遞迴切分把「## zsh 與 Powerlevel10k」這行標題黏到了前一塊的尾巴（因為標題和它前面那段之間只有一個空白行），正文反而在下一塊，所以用遞迴切分時要先把標題行併進它底下的段落。

token 與字元的換算：`qwen3-embedding:0.6b` 的 tokenizer 處理這份中文語料平均每字元約 0.54 token，300 字元大約 160 token，比英文的「4 字元 1 token」密得多。

### 2-2-2 embedding 模型

Ollama 的 embedding 端點是 `POST /api/embed`，一次可以送多句。本機下載了兩個模型比較：

| 模型 | 大小 | 向量維度 | context | 4 句耗時 | 備註 |
|---|---|---|---|---|---|
| `qwen3-embedding:0.6b` | 639 MB | 1024 | 32768 | 0.91 s | Q8_0 GGUF，llamacpp runner |
| `embeddinggemma` | 621 MB | 768 | 2048 | 0.65 s | BF16，context 只有 2K，長文件要切得更小 |

```sh
ollama pull qwen3-embedding:0.6b
ollama show qwen3-embedding:0.6b     # embedding length 1024, context length 32768
curl -s localhost:11434/api/embed -d '{"model":"qwen3-embedding:0.6b","input":["本機模型","Ollama 是什麼"]}'
```

Python 用 `ollama.embed(model=..., input=[...]).embeddings`。兩個模型回傳的向量長度都是 1.0000（已正規化），所以內積就等於餘弦相似度。

embedding 模型和 qwen3.6 可以同時留在 GPU 記憶體，實測 `ollama ps`：

```
NAME                            SIZE      PROCESSOR    CONTEXT    RUNNER
embeddinggemma:latest           685 MB    100% GPU     2048       llamacpp
qwen3-embedding:0.6b            3.0 GB    100% GPU     32768      llamacpp
qwen3.6:35b-a3b-coding-mxfp8    39 GB     100% GPU     262144     mlx
```

`qwen3-embedding:0.6b` 檔案只有 639 MB，載入後佔 3.0 GB，差額是 32K context 的 KV cache。

### 2-2-3 向量資料庫

向量資料庫做兩件事：存「向量 + 原文 + 來源」，以及「給一個查詢向量，回傳最近的 k 筆」。本章實作兩種，程式都在 `examples/ch02/`：

| | sqlite-vec | Qdrant |
|---|---|---|
| 形式 | SQLite 擴充套件，一個 `.db` 檔 | 獨立服務，用 Docker 跑 |
| 安裝 | `pip install sqlite-vec` | `docker run ... qdrant/qdrant`（映像檔 292 MB） |
| 適合 | 個人、單機、幾千到幾十萬塊 | 多人、大量資料、需要依欄位過濾 |
| 距離 | 預設 L2，越小越近 | 建 collection 時指定 Cosine，越大越近 |
| 本機實測 | v0.1.9，SQLite 3.54.1 | v1.20.0 |

> `chromadb` 在這台機器的 Python 3.15 上 `pip install` 成功但 `import chromadb` 失敗（pydantic import error），所以本章不用它。

**(a) sqlite-vec**：`store_sqlite.py` 建兩張表，`chunks` 放原文，`vec_chunks` 是 `vec0` 虛擬表放 1024 維向量，用 `id` 對應。

```
$ python store_sqlite.py
已索引 16 塊到 rag.db（4152 KB）

查詢：模型檔放在哪個資料夾？
  L2 距離 0.797  02-ollama-安裝與服務.md › 模型存放位置
  L2 距離 1.054  03-ollama-模型選擇.md › 主力模型
  L2 距離 1.080  04-ollama-api-注意事項.md › 多模型同時載入
```

查詢語法是 `WHERE embedding MATCH ? AND k = ? ORDER BY distance`，向量要用 `struct.pack` 成 float32 的 bytes 傳入。

**(b) Qdrant**：

```sh
docker run -d --name qdrant -p 6333:6333 -v qdrant_storage:/qdrant/storage qdrant/qdrant
python store_qdrant.py
docker rm -f qdrant          # 用完移除容器；資料留在 qdrant_storage volume
```

```
Qdrant 版本： 1.20.0
已寫入 16 點，collection 狀態 green，points_count 16

查詢：模型檔放在哪個資料夾？
  score 0.683  02-ollama-安裝與服務.md › 模型存放位置
  score 0.445  03-ollama-模型選擇.md › 主力模型
  score 0.417  04-ollama-api-注意事項.md › 多模型同時載入

同一查詢，只搜 04-ollama-api-注意事項.md：
  score 0.417  04-ollama-api-注意事項.md › 多模型同時載入
  score 0.391  04-ollama-api-注意事項.md › structured output 不可用
  score 0.349  04-ollama-api-注意事項.md › Ollama API 注意事項
```

兩種資料庫對同一查詢回傳的前三名完全相同。Qdrant 多做到的是最後那段：在 `points/query` 裡加 `filter`，向量搜尋同時過濾 `source` 欄位。`store_qdrant.py` 只用標準庫 `urllib` 呼叫 REST API（`PUT /collections/{name}`、`PUT /collections/{name}/points`、`POST /collections/{name}/points/query`），不需要額外套件。

## 2-3 現成工具

不想寫程式的話，這兩個工具都能「上傳文件 → 用本機 Ollama 回答」。兩個都在這台機器裝起來跑過，而且都用 `qwen3-embedding:0.6b` 做 embedding、`qwen3.6` 回答。

| | AnythingLLM 1.19.0 | Open WebUI 0.12.5 |
|---|---|---|
| 形式 | 原生 macOS App（arm64） | Docker 容器，瀏覽器操作 |
| 安裝 | `brew install --cask anythingllm`（DMG 584 MB） | `docker pull ghcr.io/open-webui/open-webui:main`（5.82 GB） |
| 資料位置 | `~/Library/Application Support/anythingllm-desktop/storage/` | Docker volume `open-webui` |
| 預設 embedding | 內建 all-MiniLM-L6-v2（可改 Ollama） | sentence-transformers/all-MiniLM-L6-v2（可改 Ollama） |
| 預設向量庫 | LanceDB（內建，storage/lancedb/） | ChromaDB（內建） |
| 預設切分 | 一份 447 token 的文件 = 1 個向量 | chunk 1000 / overlap 100 字元，同一份文件切成 3 塊 |
| 本機 API | `127.0.0.1:3001`（單人模式免登入） | `localhost:3000`，JWT 或 API key |
| qwen3.6 的思考 | 無法關閉，`<think>` 內容會進回答（本次 3,421 字元） | 請求帶 `params.think=false` 可關 |
| 多人 | 要另外開 multi-user mode | 內建帳號與權限 |

### 2-3-1 AnythingLLM

```sh
brew install --cask anythingllm      # 安裝到 /Applications/AnythingLLM.app
open -a AnythingLLM
```

App 開啟後會在本機開兩個 port：`127.0.0.1:3001` 是主伺服器，`127.0.0.1:8888` 是文件處理器（collector）。所有設定都存在 `~/Library/Application Support/anythingllm-desktop/storage/`，裡面有 `anythingllm.db`（SQLite）、`documents/`（上傳後解析成 JSON 的文件）、`lancedb/`（向量）、`logs/`。

GUI 的操作順序是：設定（左下齒輪）→ **LLM Preference** 選 Ollama、填 `http://127.0.0.1:11434`、選模型 → **Embedding Preference** 選 Ollama、選 `qwen3-embedding:0.6b` → 回到 workspace 按上傳圖示拖入文件 → 按 **Save and Embed** → 對話。**GUI 步驟未驗證**（這台機器的 `screencapture` 沒有螢幕錄製權限，無法截圖），以下改用 App 內建的本機 API 做同樣的事，`examples/ch02/anythingllm_api.sh` 可以重跑：

```sh
# 設定 LLM 與 embedding（等同 GUI 的 LLM / Embedding Preference）
curl -X POST 127.0.0.1:3001/api/system/update-env -H "Content-Type: application/json" -d '{
  "LLMProvider":"ollama","OllamaLLMBasePath":"http://127.0.0.1:11434",
  "OllamaLLMModelPref":"qwen3.6:35b-a3b-coding-mxfp8","OllamaLLMTokenLimit":32768,
  "EmbeddingEngine":"ollama","EmbeddingBasePath":"http://127.0.0.1:11434","EmbeddingModelPref":"qwen3-embedding:0.6b"}'
# 建 workspace、上傳、嵌入
curl -X POST 127.0.0.1:3001/api/workspace/new -H "Content-Type: application/json" -d '{"name":"ollama-notes"}'
curl -X POST 127.0.0.1:3001/api/workspace/ollama-notes/upload -F "file=@corpus/02-ollama-安裝與服務.md"
curl -X POST 127.0.0.1:3001/api/workspace/ollama-notes/update-embeddings -H "Content-Type: application/json" \
  -d '{"adds":["custom-documents/02-ollama-.md-b0173e89-....json"],"deletes":[]}'
```

實測結果：

```
{"vectorCount":1}                                  ← 447 token 的文件只有 1 個向量
POST /api/v1/workspace/ollama-notes/chat  mode=query
answer: Ollama 的 log 檔位於 `/opt/homebrew/var/log/ollama.log`。
        服務設定檔位於 `~/Library/LaunchAgents/sh.brew.ollama.plist`。
sources: [('02-ollama-安裝與服務.md', 0.708)]
metrics: prompt 524 + completion 1037 tokens, 6.5 s, 158.8 tok/s, provider OllamaAILLM
```

答案正確，但 1,037 個輸出 token 裡有 3,421 字元是 qwen3.6 的 `<think>` 內容，AnythingLLM 沒有把它關掉也沒有從 `textResponse` 去掉（GUI 會把 `<think>` 收合顯示）。用 API 要自己切掉 `</think>` 之前的字。另外 `update-embeddings` 要的是 `documents/custom-documents/` 裡的 JSON 檔名，不是原始檔名，上傳的回應不會告訴你，得自己去 storage 目錄看。

> 本機狀態：AnythingLLM 已安裝並設定成 Ollama，留有 workspace `ollama-notes`。不需要可以 `brew uninstall --cask anythingllm` 並刪除上述 storage 目錄。

### 2-3-2 Open WebUI 知識庫

```sh
docker run -d --name open-webui -p 3000:8080 \
  --add-host=host.docker.internal:host-gateway \
  -e OLLAMA_BASE_URL=http://host.docker.internal:11434 \
  -v open-webui:/app/backend/data \
  ghcr.io/open-webui/open-webui:main
curl localhost:3000/health          # {"status":true}
curl localhost:3000/api/version     # {"version":"0.12.5"}
```

容器裡要用 `host.docker.internal` 才連得到 Mac 上的 Ollama。第一個註冊的帳號自動是 admin。這台機器下載映像檔花了約 10 分鐘（和 Nemotron 一起搶 11 MB/s 的頻寬），啟動到 health 通過約 30 秒。

GUI 的路徑是：**Workspace → Knowledge → +** 建知識庫並上傳檔案；對話時輸入 `#` 選知識庫；embedding 模型在 **Admin Panel → Settings → Documents** 改成 Ollama。**GUI 步驟未驗證**，以下用 REST API 走完同樣流程，`examples/ch02/openwebui_api.sh` 可以重跑。Open WebUI 的 `/openapi.json` 在正式映像檔是關閉的（回 HTML），下面的端點都是實際打通的：

| 步驟 | 端點 | 實測結果 |
|---|---|---|
| 註冊 admin | `POST /api/v1/auths/signup` | 回 `token`（JWT）、`role: admin` |
| 列模型 | `GET /api/models` | 4 個 Ollama 模型，`owned_by: ollama` |
| 改 embedding | `POST /api/v1/retrieval/embedding/update` | 欄位要大寫 `RAG_EMBEDDING_ENGINE` / `RAG_EMBEDDING_MODEL`，小寫會 422 |
| 上傳 | `POST /api/v1/files/`（multipart `file`） | 回 file id；log 顯示「Using markdown header text splitter」切成 3 塊 |
| 等處理 | `GET /api/v1/files/{id}/process/status` | `processing` → `completed`（約 2 秒） |
| 建知識庫 | `POST /api/v1/knowledge/create` | `{"name","description","access_control":null}` |
| 加文件 | `POST /api/v1/knowledge/{id}/file/add` | `{"file_id"}` |
| 提問 | `POST /api/chat/completions` | `files: [{"type":"collection","id":...}]` |

```
http 200 in 3.46s
content: 根據提供的資訊，Ollama 的 log 檔位於 `/opt/homebrew/var/log/ollama.log` [1]。
         服務設定檔則位於 `~/Library/LaunchAgents/sh.brew.ollama.plist` [1]。
usage: prompt 861 tokens, completion 52
sources distances: [0.841, 0.84, 0.751]
```

兩個踩到的坑：

1. **沒關思考會卡住。** 第一次提問沒帶 `params.think=false`，qwen3.6 進入思考後 6 分鐘都沒回，Ollama 這邊 `ollama stop` 也停在 `Stopping...`，最後是 `kill -9` MLX runner 子行程才恢復（之後所有排隊的請求才動）。在請求裡加 `"params": {"think": false}` 後，同樣問題 3.5 秒回答。GUI 對應的位置是模型的 **Advanced Params**。
2. **chunk 比自己寫的大。** 預設 `CHUNK_SIZE 1000 / CHUNK_OVERLAP 100`，`TOP_K 3`，所以 prompt 用了 861 tokens（自己寫的 rag.py 同一題只用 415）。可在 `GET /api/v1/retrieval/config` 看到全部 68 個設定值，包含 `RAG_TEMPLATE`、`ENABLE_RAG_HYBRID_SEARCH`（預設 false）、`RAG_RERANKING_MODEL`（預設空）。

```sh
docker rm -f open-webui                      # 用完移除容器；帳號、知識庫都在 volume open-webui，下次 run 回來
docker run -d --restart unless-stopped ...   # 要開機自動啟動就加 --restart unless-stopped（未驗證重開機）
```

## 2-4 自己寫一套

### 2-4-1 Python 實作

`examples/ch02/rag.py` 把前面的零件串起來：

```
chunk.py 切分 → ollama.embed → sqlite-vec (rag.db) → 檢索 top-3 → 組 prompt → ollama.chat 回答
```

prompt 的 system 訊息只有一句：「只根據提供的資料回答，答案後面用 [編號] 標註引用的段落。資料裡沒有就說不知道。」每段資料前面加 `[1] 來源 檔名 › 小節`，模型就能標引用。

```
$ python rag.py "Ollama 的模型檔放在哪裡？可以改位置嗎？"

[qwen3.6:35b-a3b-coding-mxfp8] 回答：
Ollama 的模型預設存放在 `~/.ollama/models` 目錄下，其中包含 `blobs` 和 `manifests`
兩個資料夾 [1]。可以透過設定 `OLLAMA_MODELS` 環境變數來更改模型的存放位置 [1]。

引用的段落：[1] 02-ollama-安裝與服務.md › 模型存放位置, [2] 04-ollama-api-注意事項.md › Ollama API 注意事項, [3] 02-ollama-安裝與服務.md › Ollama 安裝與背景服務
檢索 0.0s，生成 21.7s，50.9 tok/s，prompt 415 tokens
```

第一次跑的 21.7 秒包含把 qwen3.6 載回 GPU（模型閒置 5 分鐘會被釋放）。模型在記憶體時同樣流程是 0.7 秒。

資料裡沒有的問題：

```
$ python rag.py "台北 101 有多高？"
[qwen3.6:35b-a3b-coding-mxfp8] 回答：
不知道 [1]
```

模型照指示回「不知道」，不會從自己的知識編答案。

### 2-4-2 rerank

向量相似度是「快但粗」的排序：embedding 模型只有 0.6B，而且查詢和段落是分開編碼的。rerank 是第二階段，先用向量取較多候選（8 塊），再用更強的模型逐一判斷「這段能不能回答這個問題」，只留前 3 塊給生成。

Ollama 0.40.13 沒有 rerank API（`/api/rerank` 回 404），library 裡也拉不到 `qwen3-reranker` 或 `bge-reranker-v2-m3`（manifest unknown）。所以 `rag.py --rerank` 用 qwen3.6 自己當 reranker：對每個候選問「這段落能回答問題的程度，0 到 10 分，只輸出一個整數」，`think=False`、`temperature=0`、`num_predict=4`。

實測問題「為什麼走 OpenAI 相容 API 時回答內容會是空的？」：

```
$ python rag.py --rerank "為什麼走 OpenAI 相容 API 時回答內容會是空的？"
向量排序（前 8）：
  0.834  04-ollama-api-注意事項.md › Ollama API 注意事項
  0.864  04-ollama-api-注意事項.md › 工具呼叫
  0.867  04-ollama-api-注意事項.md › 思考模式          ← 真正的答案在第 3 名
  0.919  04-ollama-api-注意事項.md › structured output 不可用
  ...
LLM 重排後（前 3）：
  10 分  04-ollama-api-注意事項.md › 思考模式          ← 升到第 1 名
   8 分  04-ollama-api-注意事項.md › structured output 不可用
   0 分  04-ollama-api-注意事項.md › Ollama API 注意事項

[qwen3.6:35b-a3b-coding-mxfp8] 回答：
因為 OpenAI 相容 API 不接受 `think` 參數，必須使用 `"reasoning_effort": "none"` 來關閉思考模式。
如果不這樣做，`max_tokens` 會被思考內容佔用，導致 `content` 為空 [1]。

檢索 1.5s，生成 0.7s，108.7 tok/s，prompt 342 tokens
```

| | 不 rerank | rerank |
|---|---|---|
| 答案段落的名次 | 第 3 | 第 1 |
| 檢索耗時 | 0.0 s | 1.5 s（8 次 LLM 打分） |
| 最終答案 | 正確，引用 [3] | 正確，引用 [1] |

這題不 rerank 也答對，因為 top-3 剛好有包含答案。rerank 的價值在候選多、答案落在第 4 名以後的時候；代價是每個候選多一次 LLM 呼叫，在這台機器上每次約 0.2 秒。

### 2-4-3 換成 Super VL 回答

`rag.py` 的生成模型由環境變數 `RAG_MODEL` 決定，檢索部分完全不變：

```sh
RAG_MODEL=nemotron-3.5-super python rag.py "Ollama 的模型檔放在哪裡？可以改位置嗎？"
```

> **待模型下載完成後驗證。** `nemotron-3.5-super` 是 84 GiB（82.35 GiB 權重 + 1.61 GiB 視覺 projector），這台機器以 11 MB/s 下載約需 2 小時。它和 qwen3.6（38 GB）加起來超過 GPU 可用的 107.5 GiB，Ollama 會先卸載 qwen3.6 再載入 Nemotron；embedding 模型（3 GB）可以留著，所以檢索不受影響，只有生成那一步換模型。預期差異：載入時間（84 GiB 從 SSD 讀進記憶體）、tok/s（dense 架構會明顯慢於 MoE 的 qwen3.6），以及長 context 時的 KV cache 記憶體。數字待補。

## 2-5 本章小結

| 項目 | 本機實測 |
|---|---|
| embedding 模型 | `qwen3-embedding:0.6b`，1024 維，4 句 0.91 秒，可與 qwen3.6 同時載入 |
| 切分 | 結構感知 `by_heading`：4 份文件 → 16 塊（平均 184 字元 / 99 token），10 題 top-1 全中；固定長度與遞迴各掉一題到第 2–3 名 |
| 向量庫 | sqlite-vec（單檔 4 MB）與 Qdrant 1.20.0（Docker）前三名結果一致 |
| 自己寫 | `rag.py`：3 段 ≈ 400 prompt tokens，模型在記憶體時 0.7 秒回答，資料外的問題答「不知道」 |
| rerank | 無 rerank API / 模型，用 qwen3.6 打分；8 個候選 1.5 秒，答案段落從第 3 升到第 1 |
| AnythingLLM | 可用，但 `<think>` 會進回答 |
| Open WebUI | 可用，要帶 `params.think=false`；prompt 比自寫版多一倍 |
| Nemotron 3.5 Super 回答 | 待下載完成後驗證 |

沒做到的：`chromadb` 在 Python 3.15 無法 import；兩個 GUI 工具的畫面操作沒有截圖驗證（改用它們的 API 驗證同一流程）；`--restart unless-stopped` 沒有重開機測試。
