"""
2-2-1 比較三種切法的檢索效果。

對 corpus/ 的 4 份文件分別用 heading / fixed / recursive 切分、用 qwen3-embedding:0.6b 做向量，
再拿 10 個已知答案位置的問題去檢索，看正確段落有沒有出現在前 1 名、前 3 名。

執行： python chunk_compare.py
"""
import numpy as np
import ollama

from chunk import METHODS, load_corpus

EMBED_MODEL = "qwen3-embedding:0.6b"

# (問題, 正確段落一定會包含的字串)
QUESTIONS = [
    ("Ollama 怎麼設成開機自動啟動？", "brew services start"),
    ("Ollama 的模型檔放在哪個目錄？", "~/.ollama/models"),
    ("主力模型是哪一個？", "qwen3.6:35b-a3b-coding-mxfp8"),
    ("用 OpenAI 相容 API 時要怎麼關閉思考？", "reasoning_effort"),
    ("送 format 參數為什麼會出錯？", "structured output is unavailable"),
    ("iTerm2 字型選單找不到 MesloLGS 怎麼辦？", "CTFontManagerRegisterFontsForURL"),
    ("可以同時載入幾個模型？", "OLLAMA_MAX_LOADED_MODELS"),
    ("副螢幕要排在主螢幕右邊，origin 要設多少？", "(1920,0)"),
    ("embedding 模型輸出幾維向量？", "1024"),
    ("怎麼確認模型整個跑在 GPU 上？", "100% GPU"),
]


def embed(texts: list[str]):
    r = ollama.embed(model=EMBED_MODEL, input=texts)
    vecs = np.array(r.embeddings, dtype=np.float32)
    return vecs / np.linalg.norm(vecs, axis=1, keepdims=True), r.prompt_eval_count


def main():
    qvecs, _ = embed([q for q, _ in QUESTIONS])
    print(f"{'切法':9} {'塊數':>4} {'平均字元':>6} {'平均token':>8} {'top-1':>6} {'top-3':>6}")
    for method in METHODS:
        chunks = load_corpus(method)
        cvecs, tokens = embed([c.text for c in chunks])
        sims = qvecs @ cvecs.T                       # 餘弦相似度（向量已正規化）
        top1 = top3 = 0
        misses = []
        for (q, key), row in zip(QUESTIONS, sims):
            order = np.argsort(-row)
            ranked = [chunks[i].text for i in order[:3]]
            if key in ranked[0]:
                top1 += 1
            elif any(key in t for t in ranked):
                misses.append(f"第 1 名沒命中（第 2–3 名有）：{q}")
            if any(key in t for t in ranked):
                top3 += 1
            else:
                misses.append(f"前 3 名都沒命中：{q}")
        avg_chars = sum(len(c.text) for c in chunks) // len(chunks)
        print(f"{method:9} {len(chunks):4d} {avg_chars:6d} {tokens // len(chunks):8d} "
              f"{top1:3d}/10 {top3:3d}/10")
        for m in misses:
            print(f"          {m}")


if __name__ == "__main__":
    main()
