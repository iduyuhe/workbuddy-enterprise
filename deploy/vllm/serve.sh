#!/usr/bin/env bash
# vLLM / SGLang 启动脚本样例（私有化推理引擎）
# 用法：bash deploy/vllm/serve.sh
set -euo pipefail

# ---- 通用旗舰（Qwen3-235B-A22B, FP8）----
docker run --gpus all --shm-size=32g \
  -p 8080:8080 \
  vllm/vllm-openai:latest \
  --model Qwen/Qwen3-235B-A22B-FP8 \
  --tensor-parallel-size "${VLLM_TP:-8}" \
  --dtype auto --enable-prefix-caching \
  --host 0.0.0.0 --port 8080

# ---- DeepSeek 专用（SGLang）----
# docker run --gpus all --shm-size=32g -p 8081:8081 \
#   lmsysorg/sglang:latest \
#   --model-path deepseek-ai/DeepSeek-V3 --host 0.0.0.0 --port 8081
