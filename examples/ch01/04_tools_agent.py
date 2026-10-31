"""
最小可用的 Agent 迴圈：模型決定要呼叫哪個工具，程式執行後把結果回傳給模型，
直到模型不再呼叫工具為止。

工具都是真的會執行的本機函式（只做讀取，不會改動檔案）。

執行： python 04_tools_agent.py "現在幾點？順便算一下 2 的 20 次方"
       python 04_tools_agent.py "列出目前資料夾有哪些檔案，並讀 requirements.txt 的內容"
"""
import ast
import datetime
import json
import operator
import os
import sys

import ollama

MODEL = "qwen3.6:35b-a3b-coding-mxfp8"


# ---------- 工具本體 ----------
def get_current_time() -> str:
    """取得目前的本機日期與時間。"""
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


_OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
        ast.Div: operator.truediv, ast.Pow: operator.pow, ast.USub: operator.neg}


def calculate(expression: str) -> str:
    """計算一個算術式，例如 "2 ** 20" 或 "(3 + 4) * 5"。只支援 + - * / ** 和括號。"""
    def ev(node):
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.BinOp):
            return _OPS[type(node.op)](ev(node.left), ev(node.right))
        if isinstance(node, ast.UnaryOp):
            return _OPS[type(node.op)](ev(node.operand))
        raise ValueError(f"不支援的語法: {ast.dump(node)}")
    return str(ev(ast.parse(expression, mode="eval").body))


def list_directory(path: str = ".") -> str:
    """列出資料夾內的檔案與子資料夾名稱。"""
    return json.dumps(sorted(os.listdir(path)), ensure_ascii=False)


def read_text_file(path: str) -> str:
    """讀取一個文字檔的內容（最多 4000 字元）。"""
    with open(path, encoding="utf-8") as f:
        return f.read(4000)


TOOLS = {f.__name__: f for f in (get_current_time, calculate, list_directory, read_text_file)}


# ---------- Agent 迴圈 ----------
def run(prompt: str, max_rounds: int = 8) -> str:
    messages = [{"role": "user", "content": prompt}]
    for _ in range(max_rounds):
        # ollama 套件可以直接把 Python 函式當作工具傳入，它會從 docstring 和型別註記產生 schema
        resp = ollama.chat(model=MODEL, messages=messages, tools=list(TOOLS.values()), think=False)
        msg = resp.message
        messages.append(msg)

        if not msg.tool_calls:
            return msg.content  # 模型不再呼叫工具，回傳最終答案

        for call in msg.tool_calls:
            name, args = call.function.name, call.function.arguments
            print(f"  ↳ 呼叫 {name}({json.dumps(args, ensure_ascii=False)})", file=sys.stderr)
            try:
                result = TOOLS[name](**args)
            except Exception as e:  # 把錯誤也回傳給模型，讓它自己修正
                result = f"ERROR: {e}"
            messages.append({"role": "tool", "tool_name": name, "content": str(result)})
    return "（超過最大工具呼叫次數）"


if __name__ == "__main__":
    question = " ".join(sys.argv[1:]) or "現在幾點？順便算一下 2 的 20 次方。"
    print(run(question))
