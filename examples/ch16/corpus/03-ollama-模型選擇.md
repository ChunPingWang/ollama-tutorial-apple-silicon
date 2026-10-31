# 模型選擇

寫程式和開發 Agent 選 Qwen 系列，理由是 Apache 2.0 授權可以商業使用、支援 tool calling 和思考模式、context 最長 256K。

## 主力模型

主力模型是 qwen3.6:35b-a3b-coding-mxfp8，檔案 38GB。
它是 MoE 架構，總參數 36B，每次只啟用約 3B 參數，所以生成速度快，實測每秒約 116 到 120 tokens。
它是 MLX 格式（mxfp8 量化），是 Apple Silicon 原生的格式，用 mlx runner 執行。
預設 context 長度是 262144（256K）。

## 其他候選

要求品質更高可以選 qwen3.6:27b-coding-mxfp8（30GB）。
要求最強 Agent 能力選 qwen3-coder-next:q4_K_M（52GB）。
qwen3.8-flash-next 超過 105GB，128GB 的機器跑不動，不建議。
nemotron-3.5-super 是 84 GiB 的視覺語言模型，128GB 放得下但不能和 qwen3.6 同時載入。

## embedding 模型

RAG 用的 embedding 模型是 qwen3-embedding:0.6b，639MB，輸出 1024 維向量，context 32768。
它用 llamacpp runner 執行，可以和 qwen3.6 同時載入記憶體。
