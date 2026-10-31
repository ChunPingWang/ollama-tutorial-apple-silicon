"""
2-2-3 向量資料庫（a）：sqlite-vec。單一檔案、零服務、適合個人與小型資料。

執行： python store_sqlite.py            建立 rag.db 並做一次查詢
"""
import sqlite3
import struct
import sys
from pathlib import Path

import numpy as np
import ollama
import sqlite_vec

from chunk import load_corpus

EMBED_MODEL = "qwen3-embedding:0.6b"
DIMS = 1024
DB_PATH = Path(__file__).parent / "rag.db"


def connect(path: Path = DB_PATH) -> sqlite3.Connection:
    db = sqlite3.connect(path)
    db.enable_load_extension(True)
    sqlite_vec.load(db)
    db.enable_load_extension(False)
    return db


def to_blob(vec) -> bytes:
    return struct.pack(f"{len(vec)}f", *vec)


def build(db: sqlite3.Connection) -> int:
    db.executescript(f"""
        DROP TABLE IF EXISTS chunks;
        DROP TABLE IF EXISTS vec_chunks;
        CREATE TABLE chunks(id INTEGER PRIMARY KEY, source TEXT, title TEXT, text TEXT);
        CREATE VIRTUAL TABLE vec_chunks USING vec0(id INTEGER PRIMARY KEY, embedding float[{DIMS}]);
    """)
    chunks = load_corpus("heading")
    vecs = ollama.embed(model=EMBED_MODEL, input=[c.text for c in chunks]).embeddings
    for i, (c, v) in enumerate(zip(chunks, vecs), start=1):
        db.execute("INSERT INTO chunks VALUES (?,?,?,?)", (i, c.source, c.title, c.text))
        db.execute("INSERT INTO vec_chunks VALUES (?,?)", (i, to_blob(v)))
    db.commit()
    return len(chunks)


def search(db: sqlite3.Connection, query: str, k: int = 3) -> list[tuple[float, str, str, str]]:
    qv = ollama.embed(model=EMBED_MODEL, input=[query]).embeddings[0]
    rows = db.execute("""
        SELECT v.distance, c.source, c.title, c.text
        FROM vec_chunks v JOIN chunks c ON c.id = v.id
        WHERE v.embedding MATCH ? AND k = ?
        ORDER BY v.distance
    """, (to_blob(qv), k)).fetchall()
    return rows


if __name__ == "__main__":
    db = connect()
    n = build(db)
    print(f"已索引 {n} 塊到 {DB_PATH.name}（{DB_PATH.stat().st_size // 1024} KB）")
    q = sys.argv[1] if len(sys.argv) > 1 else "模型檔放在哪個資料夾？"
    print(f"\n查詢：{q}")
    for dist, src, title, _ in search(db, q):
        print(f"  L2 距離 {dist:.3f}  {src} › {title}")
