#!/bin/zsh
# 最基本的 REST API：/api/generate（單輪、不帶對話歷史）
MODEL=${MODEL:-qwen3.6:35b-a3b-coding-mxfp8}

echo "== 1. 不串流，一次拿到完整回答 =="
curl -s http://localhost:11434/api/generate -d "{
  \"model\": \"$MODEL\",
  \"prompt\": \"用一句話解釋什麼是 MoE 模型。\",
  \"stream\": false,
  \"think\": false
}" | python3 -c '
import json, sys
r = json.load(sys.stdin)
print(r["response"])
print("---", r["eval_count"], "tokens,", round(r["eval_count"] / (r["eval_duration"] / 1e9), 1), "tok/s")
'

echo
echo "== 2. 串流：每個 token 一行 JSON，邊生成邊印 =="
curl -sN http://localhost:11434/api/generate -d "{
  \"model\": \"$MODEL\",
  \"prompt\": \"數到五，用中文。\",
  \"think\": false
}" | python3 -c '
import json, sys
for line in sys.stdin:
    chunk = json.loads(line)
    print(chunk.get("response", ""), end="", flush=True)
print()
'
