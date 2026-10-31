"""
2-4 自己寫一套：完整 RAG 流程。
  切分 (chunk.py) → embedding → sqlite-vec 索引 → 檢索 top-k → [可選 rerank] → 交給 LLM 回答

執行：
  python rag.py "問題"                  用預設模型 qwen3.6 回答
  python rag.py --rerank "問題"         先取 8 塊再用 LLM 重排，取前 3 塊
  RAG_MODEL=nemotron-3.5-super python rag.py "問題"   換成別的生成模型（2-4-3）
"""
import os
import re
import sys
import time

import ollama

from store_sqlite import DB_PATH, build, connect, search

GEN_MODEL = os.environ.get("RAG_MODEL", "qwen3.6:35b-a3b-coding-mxfp8")
RERANK_MODEL = os.environ.get("RERANK_MODEL", "qwen3.6:35b-a3b-coding-mxfp8")


def rerank(query: str, candidates: list, top_n: int = 3) -> list:
    """用 LLM 幫每個候選段落打 0-10 分（Ollama 沒有 rerank API，也沒有 reranker 模型可拉，所以用這招）。"""
    scored = []
    for dist, src, title, text in candidates:
        prompt = (f"問題：{query}\n\n段落：\n{text}\n\n"
                  "這段落能回答問題的程度，0 到 10 分，只輸出一個整數。")
        r = ollama.chat(model=RERANK_MODEL, messages=[{"role": "user", "content": prompt}],
                        think=False, options={"temperature": 0, "num_predict": 4})
        m = re.search(r"\d+", r.message.content)
        scored.append((int(m.group()) if m else 0, dist, src, title, text))
    scored.sort(key=lambda s: (-s[0], s[1]))
    return scored[:top_n]


def answer(query: str, use_rerank: bool = False, k: int = 3):
    db = connect()
    if not db.execute("SELECT name FROM sqlite_master WHERE name='chunks'").fetchone():
        print(f"（首次執行，建立索引 {DB_PATH.name}）")
        build(db)

    t0 = time.time()
    hits = search(db, query, k=8 if use_rerank else k)
    if use_rerank:
        print("向量排序（前 8）：")
        for d, src, title, _ in hits:
            print(f"  {d:.3f}  {src} › {title}")
        ranked = rerank(query, hits)
        print("LLM 重排後（前 3）：")
        for score, d, src, title, _ in ranked:
            print(f"  {score:2d} 分  {src} › {title}")
        hits = [(d, src, title, text) for _, d, src, title, text in ranked]
    t_retrieve = time.time() - t0

    context = "\n\n".join(f"[{i}] 來源 {src} › {title}\n{text}" for i, (_, src, title, text) in enumerate(hits, 1))
    messages = [
        {"role": "system", "content": "只根據提供的資料回答，答案後面用 [編號] 標註引用的段落。資料裡沒有就說不知道。用繁體中文。"},
        {"role": "user", "content": f"資料：\n{context}\n\n問題：{query}"},
    ]
    t1 = time.time()
    r = ollama.chat(model=GEN_MODEL, messages=messages, think=False)
    t_gen = time.time() - t1

    print(f"\n[{GEN_MODEL}] 回答：\n{r.message.content}\n")
    print(f"引用的段落：{', '.join(f'[{i}] {src} › {title}' for i, (_, src, title, _) in enumerate(hits, 1))}")
    print(f"檢索 {t_retrieve:.1f}s，生成 {t_gen:.1f}s，"
          f"{r.eval_count / (r.eval_duration / 1e9):.1f} tok/s，prompt {r.prompt_eval_count} tokens")


if __name__ == "__main__":
    args = sys.argv[1:]
    use_rerank = "--rerank" in args
    q = " ".join(a for a in args if a != "--rerank") or "Ollama 的模型檔放在哪裡？可以改位置嗎？"
    answer(q, use_rerank)
