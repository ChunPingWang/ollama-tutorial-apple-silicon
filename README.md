# Ollama 本機教材（Apple M5 Max / 128 GB）

這份教材以 [`~/workspace/localhost/README.md`](../localhost/README.md) 記錄的這台電腦為對象，章節編號沿用《NVIDIA RTX Spark 地端 AI 全面玩透》的目錄，但所有內容改成在 macOS / Apple Silicon 上**實際執行過**的結果。原書 Windows / CUDA 專屬的小節保留標題，標註略過原因。

| 項目 | 規格 |
|---|---|
| 晶片 / 記憶體 | Apple M5 Max，128 GB 統一記憶體（Ollama 可用 GPU 記憶體 107.5 GiB） |
| 系統 | macOS 27.2，Homebrew `/opt/homebrew` |
| Ollama | 0.40.13，`brew services` 背景服務，`127.0.0.1:11434` |
| 主力模型 | `qwen3.6:35b-a3b-coding-mxfp8`（MoE 36B / 啟用 3B，MLX，38 GB，約 120 tok/s） |

## 章節

| 章 | 檔案 | 狀態 |
|---|---|---|
| 第五章 Ollama | [docs/05-ollama.md](docs/05-ollama.md) | 已驗證（Nemotron 3.5 Super 執行結果、`OLLAMA_HOST` 區網開放待補） |
| 第十六章 RAG | [docs/16-rag.md](docs/16-rag.md) | 已驗證（Nemotron 3.5 Super 回答待補） |
| 第十八章 Hermes Agent 入門 | [docs/18-hermes-agent-intro.md](docs/18-hermes-agent-intro.md) | 已驗證（桌面版 GUI 小節略過） |
| 第十九章 Hermes Agent 進階 | [docs/19-hermes-agent-advanced.md](docs/19-hermes-agent-advanced.md) | 已驗證（Telegram / LINE 無 token、OpenShell 未安裝） |

## 範例程式

```
examples/
  ch05/   REST API、Python（ollama / openai 套件）、工具呼叫 Agent、JSON 輸出、視覺、Modelfile
  ch16/   文件切分、embedding、sqlite-vec / Qdrant、RAG 管線、LLM rerank
  ch18/   logproxy.py：記錄 Hermes 送給 Ollama 的每個請求（第十八、十九章的觀察工具）
```

Python 範例的執行方式（Homebrew 的 Python 3.15 不允許直接 `pip install`，要用 venv）：

```sh
cd ~/workspace/ollama-tutorial
python3 -m venv .venv
source .venv/bin/activate
pip install -r examples/ch05/requirements.txt -r examples/ch16/requirements.txt
python examples/ch05/04_tools_agent.py "現在幾點？"
```

## 標註慣例

- 沒有特別標註的指令與輸出，都是 2026-10-31 在這台機器上實際執行的結果。
- **未驗證**：有文件依據但本機還沒跑過。
- **本機略過：原因**：這台電腦無法或不需要執行（例如 CUDA 專屬問題、Windows 安裝程式）。
