"""
2-2-2 embedding 模型：把文字變成向量，用餘弦相似度比較語意距離。

執行： python embed_demo.py [模型名稱]   （預設 qwen3-embedding:0.6b）
"""
import sys
import time

import numpy as np
import ollama

MODEL = sys.argv[1] if len(sys.argv) > 1 else "qwen3-embedding:0.6b"


def embed(texts: list[str]) -> np.ndarray:
    r = ollama.embed(model=MODEL, input=texts)
    return np.array(r.embeddings, dtype=np.float32)


def cosine(a: np.ndarray, b: np.ndarray) -> float:
    return float(a @ b / (np.linalg.norm(a) * np.linalg.norm(b)))


if __name__ == "__main__":
    sentences = [
        "Ollama 的模型放在 ~/.ollama/models",
        "模型檔案存放的目錄在哪裡？",
        "Docker Desktop 需要 sudo 密碼才能安裝",
        "今天晚餐想吃牛肉麵",
    ]
    t = time.time()
    vecs = embed(sentences)
    print(f"模型 {MODEL}：{len(sentences)} 句 → shape {vecs.shape}，耗時 {time.time() - t:.2f}s")
    print(f"向量是否已正規化（長度≈1）：{np.linalg.norm(vecs[0]):.4f}\n")
    q = sentences[1]
    print(f"查詢：{q}")
    for s, v in zip(sentences, vecs):
        if s != q:
            print(f"  {cosine(vecs[1], v):.3f}  {s}")
