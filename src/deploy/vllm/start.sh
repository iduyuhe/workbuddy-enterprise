#!/usr/bin/env bash
# vLLM 启动脚本
# 说明：本脚本在 vllm 容器内执行，模型权重挂载自宿主机 /models。
# 模型目录约定：/models/Qwen3-235B-A22B
set -e

MODEL_NAME="${MODEL_NAME:-Qwen/Qwen3-235B-A22B}"
MODEL_DIR="${MODEL_DIR:-/models/Qwen3-235B-A22B}"

# 若宿主机已下载好权重（/models/Qwen3-235B-A22B），优先使用本地路径
if [ -d "$MODEL_DIR" ]; then
  echo "[vllm] 使用本地权重目录: $MODEL_DIR"
  MODEL_ARG="$MODEL_DIR"
else
  echo "[vllm] 未找到本地权重，回退到 HuggingFace 仓库: $MODEL_NAME"
  MODEL_ARG="$MODEL_NAME"
fi

# --tensor-parallel-size 8 : 8 卡张量并行（需 8×GPU，单卡显存不足时调整）
# --dtype half              : 半精度（权重 FP8 量化时可用 fp8；此处默认 half 稳妥）
# --enable-auto-tool-choice : 开启工具调用/函数调用能力
# --tool-call-parser hermes : 适配 Qwen 系列工具调用解析（hermes 协议）
# --gpu-memory-utilization  : 默认 0.9，可按需调高/调低
# --max-model-len           : 上下文长度，按显存调整（235B-A22B 建议 8192~32768）
exec python -m vllm.entrypoints.openai.api_server \
  --model "$MODEL_ARG" \
  --host 0.0.0.0 \
  --port 8000 \
  --served-model-name qwen3-235b-a22b \
  --tensor-parallel-size 8 \
  --dtype half \
  --enable-auto-tool-choice \
  --tool-call-parser hermes \
  --gpu-memory-utilization 0.90 \
  --max-model-len 32768 \
  --enable-prefix-caching
