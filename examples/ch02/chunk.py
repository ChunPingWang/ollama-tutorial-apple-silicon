"""
2-2-1 切分文件：兩種常見做法。

1. by_heading : 依 Markdown 標題切，一個小節一塊。語意完整，但長度不一。
2. fixed_size : 固定字元數切，相鄰兩塊重疊 overlap 字元，避免句子被切在邊界而丟失上下文。

執行： python chunk.py   （印出 corpus/ 的切分結果統計）
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


def load_corpus(method: str = "heading") -> list[Chunk]:
    out = []
    for p in sorted(CORPUS.glob("*.md")):
        out += by_heading(p) if method == "heading" else fixed_size(p)
    return out


if __name__ == "__main__":
    for method in ("heading", "fixed"):
        chunks = load_corpus(method)
        lens = [len(c.text) for c in chunks]
        print(f"[{method:7}] {len(chunks):2d} 塊，長度 min {min(lens)} / avg {sum(lens)//len(lens)} / max {max(lens)} 字元")
    print("\n依標題切的前三塊：")
    for c in load_corpus("heading")[:3]:
        print(f"  - {c.source} › {c.title}（{len(c.text)} 字元）")
