#!/bin/bash
# vLLM server for the ALFWorld ladder (same settings as the 2026-11-15 feasibility run, FP8 model).
cd ~/test-a-feasibility
export VLLM_ATTENTION_BACKEND=FLASH_ATTN VLLM_USE_FLASHINFER_SAMPLER=0
exec .venv-vllm/bin/python -m vllm.entrypoints.openai.api_server \
  --model ~/test-a-feasibility/models/Qwen3-4B-Instruct-2507-FP8 \
  --served-model-name Qwen/Qwen3-4B-Instruct-2507-FP8 \
  --host 127.0.0.1 --port 8001 --max-model-len 16384 \
  --gpu-memory-utilization 0.80 --enforce-eager --seed 0
