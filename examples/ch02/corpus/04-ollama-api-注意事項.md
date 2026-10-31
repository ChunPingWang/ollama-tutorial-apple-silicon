# Ollama API 注意事項

Ollama 有兩套 API：原生 API 在 http://localhost:11434/api，OpenAI 相容 API 在 http://localhost:11434/v1。

## 思考模式

qwen3.6 預設會思考（thinking）。
原生 API 用 "think": false 關閉。
OpenAI 相容 API 不接受 think 參數，要用 "reasoning_effort": "none" 關閉，否則 max_tokens 會被思考內容吃掉，content 會是空的。

## structured output 不可用

MLX runner 不支援 format 參數。送 format 會回傳錯誤 "structured output is unavailable"。
log 裡的原因是找不到 libollama_xgrammar.dylib。
替代做法是在提示詞要求只輸出 JSON，程式端用 pydantic 驗證，失敗就把錯誤丟回去讓模型重試。
GGUF 模型走 llamacpp runner，format 參數可以用。

## 工具呼叫

原生 API 和 OpenAI 相容 API 都支援 tools。
工具結果用 role 為 tool 的訊息回傳，原生 API 要帶 tool_name。
Python 的 ollama 套件可以直接把函式當作工具傳入，它會從 docstring 和型別註記產生 schema。

## 多模型同時載入

OLLAMA_MAX_LOADED_MODELS 預設是 0，表示由 Ollama 依記憶體自動決定。
實測 qwen3.6（40GB）和 qwen3-embedding:0.6b（3GB）可以同時留在 GPU 記憶體。
模型預設閒置 5 分鐘後釋放，由 OLLAMA_KEEP_ALIVE 或請求裡的 keep_alive 控制。
