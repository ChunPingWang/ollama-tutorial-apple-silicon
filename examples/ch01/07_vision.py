"""
模型 capabilities 有 vision，可以直接餵圖片。
這裡先用純標準庫產生一張測試用 PNG（紅底、中間一個藍色方塊），再請模型描述。
實務上把 images 換成自己的 .png / .jpg 路徑即可。

執行： python 07_vision.py [圖片路徑]
"""
import struct
import sys
import zlib

import ollama

MODEL = "qwen3.6:35b-a3b-coding-mxfp8"


def make_test_png(path: str, size: int = 128) -> str:
    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data))
    rows = b""
    for y in range(size):
        row = bytearray([0])  # filter type
        for x in range(size):
            inside = size // 4 <= x < size * 3 // 4 and size // 4 <= y < size * 3 // 4
            row += bytes((40, 80, 220) if inside else (220, 40, 40))
        rows += bytes(row)
    png = (b"\x89PNG\r\n\x1a\n"
           + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0))
           + chunk(b"IDAT", zlib.compress(rows))
           + chunk(b"IEND", b""))
    with open(path, "wb") as f:
        f.write(png)
    return path


if __name__ == "__main__":
    image = sys.argv[1] if len(sys.argv) > 1 else make_test_png("/tmp/ollama_vision_test.png")
    r = ollama.chat(
        model=MODEL,
        messages=[{"role": "user", "content": "這張圖裡有什麼？用一句話描述顏色和形狀。", "images": [image]}],
        think=False,
    )
    print(r.message.content)
