#!/bin/zsh
# 2-3-2 用 REST API 操作 Open WebUI 知識庫（本機 Docker，port 3000）。
# 第一次執行會註冊管理員帳號；之後重跑請改用 /api/v1/auths/signin。
set -e
B=http://localhost:3000
DOC=${1:-corpus/02-ollama-安裝與服務.md}

echo "== 1. 註冊第一個帳號（自動成為 admin），拿到 JWT =="
TOKEN=$(curl -s $B/api/v1/auths/signup -H "Content-Type: application/json" \
  -d '{"name":"admin","email":"admin@example.com","password":"Passw0rd!"}' | python3 -c 'import sys,json; print(json.load(sys.stdin)["token"])')
H=(-H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json")

echo "== 2. Open WebUI 看到的模型（來自 Ollama）=="
curl -s $B/api/models -H "Authorization: Bearer $TOKEN" | python3 -c 'import sys,json; [print(" ", m["id"]) for m in json.load(sys.stdin)["data"]]'

echo "== 3. embedding 改用 Ollama 的 qwen3-embedding:0.6b（欄位名要大寫）=="
curl -s $B/api/v1/retrieval/embedding/update $H -d '{"RAG_EMBEDDING_ENGINE":"ollama","RAG_EMBEDDING_MODEL":"qwen3-embedding:0.6b","RAG_EMBEDDING_BATCH_SIZE":1,"ollama_config":{"url":"http://host.docker.internal:11434","key":""}}' \
  | python3 -c 'import sys,json; d=json.load(sys.stdin); print(" ", d["RAG_EMBEDDING_ENGINE"], d["RAG_EMBEDDING_MODEL"])'

echo "== 4. 上傳文件，等它切分 + embedding 完成 =="
FID=$(curl -s $B/api/v1/files/ -H "Authorization: Bearer $TOKEN" -F "file=@$DOC" | python3 -c 'import sys,json; print(json.load(sys.stdin)["id"])')
until curl -s $B/api/v1/files/$FID/process/status -H "Authorization: Bearer $TOKEN" | grep -q completed; do sleep 1; done
echo "  file id $FID 處理完成"

echo "== 5. 建立知識庫並加入文件 =="
KB=$(curl -s $B/api/v1/knowledge/create $H -d '{"name":"ollama-tutorial","description":"本機 Ollama 筆記","access_control":null}' | python3 -c 'import sys,json; print(json.load(sys.stdin)["id"])')
curl -s $B/api/v1/knowledge/$KB/file/add $H -d "{\"file_id\":\"$FID\"}" > /dev/null
echo "  knowledge id $KB"

echo "== 6. 針對知識庫提問（params.think=false 關掉 qwen3.6 的思考，否則會等很久）=="
curl -s $B/api/chat/completions $H -d "{
  \"model\": \"qwen3.6:35b-a3b-coding-mxfp8\",
  \"messages\": [{\"role\": \"user\", \"content\": \"Ollama 的 log 檔在哪裡？服務設定檔在哪？\"}],
  \"files\": [{\"type\": \"collection\", \"id\": \"$KB\"}],
  \"stream\": false,
  \"params\": {\"think\": false}
}" | python3 -c '
import sys, json
d = json.load(sys.stdin)
print(d["choices"][0]["message"]["content"])
print("prompt tokens:", d["usage"]["prompt_tokens"], "| 檢索到的片段距離:", d["sources"][0]["distances"])'
