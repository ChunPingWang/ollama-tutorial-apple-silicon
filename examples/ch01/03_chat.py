"""
用官方 ollama Python 套件做一個最簡單的終端機聊天程式。
- 串流輸出
- 自己維護 messages 以保留對話歷史
- 預設關閉思考模式 (think=False)，速度快；要看模型推理過程改成 True

執行： python 03_chat.py            （輸入 exit 或 Ctrl-D 離開）
"""
import sys

import ollama

MODEL = sys.argv[1] if len(sys.argv) > 1 else "qwen3.6:35b-a3b-coding-mxfp8"
messages = [{"role": "system", "content": "你是在 macOS 上運作的本機助理，請用繁體中文回答。"}]

print(f"模型：{MODEL}（輸入 exit 離開）")
while True:
    try:
        user = input("\n你> ").strip()
    except EOFError:
        break
    if not user or user.lower() in {"exit", "quit"}:
        break
    messages.append({"role": "user", "content": user})

    print("AI> ", end="", flush=True)
    reply = ""
    for chunk in ollama.chat(model=MODEL, messages=messages, stream=True, think=False):
        piece = chunk.message.content or ""
        print(piece, end="", flush=True)
        reply += piece
    print()
    messages.append({"role": "assistant", "content": reply})
