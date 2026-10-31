#!/bin/zsh
# 檢查這台電腦的 Ollama 是否正常。任何一步失敗都會直接停下。
set -e
echo "== 版本 =="
ollama --version
echo
echo "== 背景服務 (brew services) =="
brew services info ollama | grep -E "Running|PID"
echo
echo "== API 是否回應 =="
curl -sf --max-time 5 http://localhost:11434/api/version
echo
echo
echo "== 已下載的模型 =="
ollama list
echo
echo "== 目前載入記憶體的模型 (空白表示沒有) =="
ollama ps
echo
echo "== 模型佔用的磁碟空間 =="
du -sh ~/.ollama/models
echo
echo "== 最近 5 行 log =="
tail -n 5 /opt/homebrew/var/log/ollama.log
