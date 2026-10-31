#!/bin/zsh
# 16-3-1 用 AnythingLLM 桌面版內建的本機 API（127.0.0.1:3001）設定 Ollama、建 workspace、上傳文件、提問。
# 單人模式且未設密碼時，/api/* 不需要登入；/api/v1/* 需要 API key。
set -e
A=http://127.0.0.1:3001
DOC=${1:-corpus/02-ollama-安裝與服務.md}
STORAGE="$HOME/Library/Application Support/anythingllm-desktop/storage"

echo "== 1. 確認 App 在跑 =="
curl -s $A/api/ping; echo

echo "== 2. LLM 與 embedding 都指到本機 Ollama =="
curl -s -X POST $A/api/system/update-env -H "Content-Type: application/json" -d '{
  "LLMProvider":"ollama","OllamaLLMBasePath":"http://127.0.0.1:11434",
  "OllamaLLMModelPref":"qwen3.6:35b-a3b-coding-mxfp8","OllamaLLMTokenLimit":32768,
  "EmbeddingEngine":"ollama","EmbeddingBasePath":"http://127.0.0.1:11434",
  "EmbeddingModelPref":"qwen3-embedding:0.6b","EmbeddingModelMaxChunkLength":8192}' | python3 -c 'import sys,json; print(" error:", json.load(sys.stdin)["error"])'

echo "== 3. 建 workspace、上傳文件、嵌入 =="
curl -s -X POST $A/api/workspace/new -H "Content-Type: application/json" -d '{"name":"ollama-notes"}' > /dev/null || true
curl -s -X POST $A/api/workspace/ollama-notes/upload -F "file=@$DOC" | python3 -c 'import sys,json; print(" upload:", json.load(sys.stdin)["success"])'
JSON=$(ls -t "$STORAGE/documents/custom-documents/" | head -1)
curl -s -X POST $A/api/workspace/ollama-notes/update-embeddings -H "Content-Type: application/json" \
  -d "{\"adds\":[\"custom-documents/$JSON\"],\"deletes\":[]}" > /dev/null
curl -s $A/api/system/system-vectors; echo

echo "== 4. 產生 API key，用 v1 API 提問（mode=query 只根據文件回答）=="
KEY=$(curl -s -X POST $A/api/system/generate-api-key -H "Content-Type: application/json" -d '{}' | python3 -c 'import sys,json; print(json.load(sys.stdin)["apiKey"]["secret"])')
curl -s -X POST $A/api/v1/workspace/ollama-notes/chat -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" \
  -d '{"message":"Ollama 的 log 檔在哪裡？服務設定檔在哪？","mode":"query"}' | python3 -c '
import sys, json
d = json.load(sys.stdin)
t = d["textResponse"]; i = t.find("</think>")
print("（思考內容", i if i > 0 else 0, "字元，已略過）")
print(t[i + 8:].strip() if i > 0 else t)
print("sources:", [(s["title"], round(float(s["score"]), 3)) for s in d["sources"]])
m = d["metrics"]; print("tokens:", m["prompt_tokens"], "+", m["completion_tokens"], "|", round(m["duration"], 1), "s")'
