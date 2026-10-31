# Ollama 安裝與背景服務

Ollama 用 Homebrew 安裝：brew install ollama，版本 0.40.13。
用 brew services start ollama 設成背景服務，開機自動啟動。
服務的設定檔在 ~/Library/LaunchAgents/sh.brew.ollama.plist，Homebrew 預設加上兩個環境變數：
OLLAMA_FLASH_ATTENTION=1 和 OLLAMA_KV_CACHE_TYPE=q8_0。
log 檔在 /opt/homebrew/var/log/ollama.log。
API 只監聽 127.0.0.1:11434，要開放給區域網路要設 OLLAMA_HOST=0.0.0.0。

## 模型存放位置

模型放在 ~/.ollama/models，底下有 blobs 和 manifests 兩個資料夾。
blobs 放實際的權重檔，manifests 放模型名稱到 blob 的對照。
用 OLLAMA_MODELS 環境變數可以換到別的位置。

## 確認用到 GPU

ollama ps 的 PROCESSOR 欄位顯示 100% GPU 表示整個模型都在 GPU 上。
RUNNER 欄位顯示 mlx 表示用 Apple 原生的 MLX 引擎，顯示 llamacpp 表示用 llama.cpp 的 Metal 後端。
log 裡會看到 inference compute library=Metal name=MTL0 description="Apple M5 Max" total="107.5 GiB"。
macOS 預設只讓 GPU 使用大約 107.5 GiB，剩下的留給系統。
