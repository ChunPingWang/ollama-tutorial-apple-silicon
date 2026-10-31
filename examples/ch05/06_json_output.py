"""
要模型回傳可以直接 json.loads 的結構化資料。

這台機器上的 qwen3.6:35b-a3b-coding-mxfp8 是 MLX 格式，Ollama 0.40.13 的 MLX runner
不支援 `format` 參數（API 會回 "structured output is unavailable"）。
所以改用「提示詞要求 JSON + 程式端驗證 + 失敗重試」的做法，用 pydantic 驗證欄位。

執行： python 06_json_output.py
"""
import json

import ollama
from pydantic import BaseModel, ValidationError

MODEL = "qwen3.6:35b-a3b-coding-mxfp8"


class City(BaseModel):
    name: str
    country: str
    population: int


def extract(text: str, retries: int = 3) -> City:
    schema = json.dumps(City.model_json_schema(), ensure_ascii=False)
    messages = [
        {"role": "system", "content": f"只輸出一個符合此 JSON Schema 的 JSON 物件，不要 markdown、不要說明：{schema}"},
        {"role": "user", "content": text},
    ]
    for attempt in range(retries):
        raw = ollama.chat(model=MODEL, messages=messages, think=False).message.content.strip()
        raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        try:
            return City.model_validate_json(raw)
        except ValidationError as e:
            # 把錯誤丟回去讓模型修正
            messages += [{"role": "assistant", "content": raw},
                         {"role": "user", "content": f"JSON 不合規格，請修正後只輸出 JSON：{e}"}]
    raise RuntimeError("模型連續輸出無效 JSON")


if __name__ == "__main__":
    city = extract("台北市是台灣的首都，人口大約 250 萬。")
    print(city)
    print(city.model_dump_json(indent=2))
