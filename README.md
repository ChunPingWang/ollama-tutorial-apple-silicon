# Ollama 本機教材（Apple M5 Max / 128 GB）

這份教材涵蓋 Ollama、RAG 與 Hermes Agent 四章加一個附錄，所有內容都是在 macOS / Apple Silicon 上**實際執行過**的結果。主題取材自《NVIDIA RTX Spark 地端 AI 全面玩透》，但章節自行編排；Windows / CUDA 專屬內容、訊息平台（Telegram / LINE）與 LM Studio 不在本教材範圍。

| 項目 | 規格 |
|---|---|
| 晶片 / 記憶體 | Apple M5 Max，128 GB 統一記憶體（Ollama 可用 GPU 記憶體 107.5 GiB） |
| 系統 | macOS 27.2，Homebrew `/opt/homebrew` |
| Ollama | 0.40.13，`brew services` 背景服務，`127.0.0.1:11434` |
| 主力模型 | `qwen3.6:35b-a3b-coding-mxfp8`（MoE 36B / 啟用 3B，MLX，38 GB，約 120 tok/s） |

## 章節

| 章 | 檔案 | 狀態 |
|---|---|---|
| 第一章 Ollama | [docs/01-ollama.md](docs/01-ollama.md) | 已驗證（Nemotron 3.5 Super 執行結果、`OLLAMA_HOST` 區網開放待補） |
| 第二章 RAG | [docs/02-rag.md](docs/02-rag.md) | 已驗證（Nemotron 3.5 Super 回答待補） |
| 第三章 Hermes Agent 入門 | [docs/03-hermes-agent-intro.md](docs/03-hermes-agent-intro.md) | 已驗證（桌面版建置流程待補） |
| 第四章 Hermes Agent 進階 | [docs/04-hermes-agent-advanced.md](docs/04-hermes-agent-advanced.md) | 已驗證（OpenShell 未安裝） |
| 附錄 A 模型調優參數指南 | [docs/A1-model-tuning.md](docs/A1-model-tuning.md) | 已驗證（採樣參數以 0.5B 小模型示範） |

## 範例程式

```
examples/
  ch01/   REST API、Python（ollama / openai 套件）、工具呼叫 Agent、JSON 輸出、視覺、Modelfile
  ch02/   文件切分（三種切法與命中率比較）、embedding、sqlite-vec / Qdrant、RAG 管線、LLM rerank
  ch03/   logproxy.py：記錄 Hermes 送給 Ollama 的每個請求（第三、四章的觀察工具）
```

Python 範例的執行方式（Homebrew 的 Python 3.15 不允許直接 `pip install`，要用 venv）：

```sh
cd ~/workspace/ollama-tutorial
python3 -m venv .venv
source .venv/bin/activate
pip install -r examples/ch01/requirements.txt -r examples/ch02/requirements.txt
python examples/ch01/04_tools_agent.py "現在幾點？"
```

## 標註慣例

- 沒有特別標註的指令與輸出，都是 2026-10-31 在這台機器上實際執行的結果。
- **未驗證**：有文件依據但本機還沒跑過。
- **本機略過：原因**：這台電腦無法或不需要執行。
