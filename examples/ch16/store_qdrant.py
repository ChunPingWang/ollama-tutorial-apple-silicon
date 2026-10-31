"""
16-2-3 向量資料庫（b）：Qdrant（Docker 服務）。多人、大量資料、需要過濾條件時用。
只用標準庫的 urllib 呼叫 REST API，不需要額外套件。

先啟動：
  docker run -d --name qdrant -p 6333:6333 -v qdrant_storage:/qdrant/storage qdrant/qdrant
執行： python store_qdrant.py
"""
import json
import sys
import urllib.request

import ollama

from chunk import load_corpus

EMBED_MODEL = "qwen3-embedding:0.6b"
QDRANT = "http://localhost:6333"
COLL = "ollama_tutorial"


def api(method: str, path: str, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(f"{QDRANT}{path}", data, {"Content-Type": "application/json"}, method=method)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def build() -> int:
    chunks = load_corpus("heading")
    vecs = ollama.embed(model=EMBED_MODEL, input=[c.text for c in chunks]).embeddings
    api("DELETE", f"/collections/{COLL}")
    api("PUT", f"/collections/{COLL}", {"vectors": {"size": len(vecs[0]), "distance": "Cosine"}})
    points = [{"id": i, "vector": v, "payload": {"source": c.source, "title": c.title, "text": c.text}}
              for i, (c, v) in enumerate(zip(chunks, vecs), start=1)]
    api("PUT", f"/collections/{COLL}/points?wait=true", {"points": points})
    return len(points)


def search(query: str, k: int = 3, source_filter: str | None = None):
    qv = ollama.embed(model=EMBED_MODEL, input=[query]).embeddings[0]
    body = {"query": qv, "limit": k, "with_payload": True}
    if source_filter:  # Qdrant 的強項：向量搜尋同時加 payload 過濾
        body["filter"] = {"must": [{"key": "source", "match": {"value": source_filter}}]}
    return api("POST", f"/collections/{COLL}/points/query", body)["result"]["points"]


if __name__ == "__main__":
    print("Qdrant 版本：", api("GET", "/")["version"])
    n = build()
    info = api("GET", f"/collections/{COLL}")["result"]
    print(f"已寫入 {n} 點，collection 狀態 {info['status']}，points_count {info['points_count']}")
    q = sys.argv[1] if len(sys.argv) > 1 else "模型檔放在哪個資料夾？"
    print(f"\n查詢：{q}")
    for p in search(q):
        print(f"  score {p['score']:.3f}  {p['payload']['source']} › {p['payload']['title']}")
    print("\n同一查詢，只搜 04-ollama-api-注意事項.md：")
    for p in search(q, source_filter="04-ollama-api-注意事項.md"):
        print(f"  score {p['score']:.3f}  {p['payload']['source']} › {p['payload']['title']}")
