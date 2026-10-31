#!/bin/zsh
# /api/chat：帶對話歷史的多輪對話。messages 由呼叫端自己維護。
MODEL=${MODEL:-qwen3.6:35b-a3b-coding-mxfp8}

curl -s http://localhost:11434/api/chat -d "{
  \"model\": \"$MODEL\",
  \"stream\": false,
  \"think\": false,
  \"messages\": [
    {\"role\": \"system\",    \"content\": \"你是簡潔的助理，回答不超過兩句。\"},
    {\"role\": \"user\",      \"content\": \"我叫 Rex。\"},
    {\"role\": \"assistant\", \"content\": \"你好 Rex，有什麼可以幫你？\"},
    {\"role\": \"user\",      \"content\": \"我剛剛說我叫什麼？\"}
  ]
}" | python3 -c 'import json, sys; print(json.load(sys.stdin)["message"]["content"])'
