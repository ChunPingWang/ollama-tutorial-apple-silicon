"""
2-2-1 切分文件：三種常見做法。

1. by_heading : 依 Markdown 標題切，一個小節一塊。語意完整，但長度不一。
2. fixed_size : 固定字元數切，相鄰兩塊重疊 overlap 字元，避免句子被切在邊界而丟失上下文。
3. recursive  : 遞迴切分。先用段落分，段落太長再用句子分，最後把相鄰的小片段合併到接近 size。
                （LangChain RecursiveCharacterTextSplitter 的做法）

執行： python chunk.py           （印出 corpus/ 的切分結果統計）
      python chunk_compare.py   （用 10 個問題比較三種切法的檢索命中率）
"""
import re
from dataclasses import dataclass
from pathlib import Path

CORPUS = Path(__file__).parent / "corpus"


@dataclass
class Chunk:
    source: str   # 檔名
    title: str    # 所屬標題
    text: str


def by_heading(path: Path) -> list[Chunk]:
    chunks, title, buf = [], path.stem, []
    for line in path.read_text(encoding="utf-8").splitlines():
        if re.match(r"^#{1,3} ", line):
            if buf:
                chunks.append(Chunk(path.name, title, "\n".join(buf).strip()))
            title, buf = line.lstrip("# ").strip(), []
        else:
            buf.append(line)
    if buf:
        chunks.append(Chunk(path.name, title, "\n".join(buf).strip()))
    # 每塊前面加上標題，讓 embedding 知道這段在講什麼
    return [Chunk(c.source, c.title, f"{c.title}\n{c.text}") for c in chunks if c.text]


def fixed_size(path: Path, size: int = 300, overlap: int = 60) -> list[Chunk]:
    text = path.read_text(encoding="utf-8")
    chunks, start = [], 0
    while start < len(text):
        chunks.append(Chunk(path.name, path.stem, text[start:start + size]))
        start += size - overlap
    return chunks


def recursive(path: Path, size: int = 300, seps: tuple[str, ...] = ("\n\n", "\n", "。", "，")) -> list[Chunk]:
    """先用最粗的分隔符切，切出來還是太長就換下一個更細的分隔符；最後把相鄰小片段合併到不超過 size。"""
    def split(text: str, level: int) -> list[str]:
        if len(text) <= size or level == len(seps):
            return [text]
        sep = seps[level]
        parts = [p + sep for p in text.split(sep) if p.strip()]
        out = []
        for part in parts:
            out += split(part, level + 1) if len(part) > size else [part]
        return out

    pieces, buf = [], ""
    for piece in split(path.read_text(encoding="utf-8"), 0):
        if len(buf) + len(piece) > size and buf:
            pieces.append(buf.strip())
            buf = ""
        buf += piece
    if buf.strip():
        pieces.append(buf.strip())
    return [Chunk(path.name, path.stem, t) for t in pieces]


METHODS = {"heading": by_heading, "fixed": fixed_size, "recursive": recursive}


def load_corpus(method: str = "heading") -> list[Chunk]:
    out = []
    for p in sorted(CORPUS.glob("*.md")):
        out += METHODS[method](p)
    return out


if __name__ == "__main__":
    for method in METHODS:
        chunks = load_corpus(method)
        lens = [len(c.text) for c in chunks]
        print(f"[{method:9}] {len(chunks):2d} 塊，長度 min {min(lens)} / avg {sum(lens)//len(lens)} / max {max(lens)} 字元")
    print("\n依標題切的前三塊：")
    for c in load_corpus("heading")[:3]:
        print(f"  - {c.source} › {c.title}（{len(c.text)} 字元）")
