"""
用 OpenAI 官方 SDK 連本機 Ollama。只要改 base_url，api_key 隨便填即可。
任何支援 OpenAI API 的工具或框架都可以用同樣方式接上。

注意：這台機器上的 qwen3.6 預設會「思考」。走 OpenAI 相容 API 時，
`think=False` 不會被接受，要用 `reasoning_effort="none"` 關閉；
否則 max_tokens 會先被思考內容吃掉，content 可能是空的。

執行： python 05_openai_compat.py
"""
from openai import OpenAI

client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
MODEL = "qwen3.6:35b-a3b-coding-mxfp8"

# 1. 一般對話（串流）
print("== 串流回答 ==")
stream = client.chat.completions.create(
    model=MODEL,
    messages=[{"role": "user", "content": "用兩句話介紹 Apple Silicon 的統一記憶體架構。"}],
    reasoning_effort="none",
    stream=True,
)
for chunk in stream:
    print(chunk.choices[0].delta.content or "", end="", flush=True)
print("\n")

# 2. 工具呼叫（OpenAI 格式）
print("== 工具呼叫 ==")
tools = [{
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "查詢城市目前天氣",
        "parameters": {"type": "object", "properties": {"city": {"type": "string"}}, "required": ["city"]},
    },
}]
r = client.chat.completions.create(
    model=MODEL,
    messages=[{"role": "user", "content": "高雄現在天氣如何？"}],
    tools=tools,
    reasoning_effort="none",
)
for call in r.choices[0].message.tool_calls or []:
    print(call.function.name, call.function.arguments)
