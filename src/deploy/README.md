# WorkBuddy Enterprise Edition — 部署说明

企业级本地化部署 AI 智能体平台。本文档描述基于 Docker Compose 的单主机起步部署方式。

## 1. 环境要求

- 操作系统：Linux（推荐 Ubuntu 22.04+），需安装 NVIDIA 驱动
- Docker Engine 24+ 与 Docker Compose v2
- NVIDIA Container Toolkit（GPU 透传）
- GPU：8× 支持 FP8 的加速卡（如 NVIDIA H100/A100），用于加载 Qwen3-235B-A22B（FP8/FP16）
- 宿主机模型目录：`/models`（请提前放置模型权重）
- 内存 ≥ 128G，磁盘 ≥ 1TB（建议 NVMe）

## 2. 模型权重放置

默认从宿主机 `/models` 挂载进 vllm 容器。放置结构：

```
/models/
  Qwen3-235B-A22B/        # Qwen3-235B-A22B 权重目录
    config.json
    model.safetensors.index.json
    ...
```

权重可通过 HuggingFace `huggingface-cli download Qwen/Qwen3-235B-A22B --local-dir /models/Qwen3-235B-A22B` 下载。若未放置，vLLM 会回退到在线拉取（需联网）。

## 3. 部署步骤

```bash
cd src/deploy
cp .env.example .env          # 按需修改 JWT_SECRET / OIDC / LANGFUSE 等
docker compose up -d          # 启动全部服务
docker compose ps             # 查看状态
docker compose logs -f vllm   # 观察推理服务启动（大模型加载较慢，约数分钟）
```

启动后访问：

- 前端 Web：http://localhost:3000
- 后端 API：http://localhost:8080 （健康检查 `/health`，指标 `/metrics`）
- vLLM：http://localhost:8000 （OpenAI 兼容 `/v1`）
- Qdrant：http://localhost:6333
- Langfuse：http://localhost:3100
- Prometheus：http://localhost:9090
- Grafana：http://localhost:3001 （默认 admin/admin）

## 4. 端口规划

| 服务      | 端口  |
|-----------|-------|
| web       | 3000  |
| langfuse  | 3100  |
| grafana   | 3001  |
| backend   | 8080  |
| vllm      | 8000  |
| qdrant    | 6333  |
| postgres  | 5432  |
| redis     | 6379  |
| prometheus| 9090  |

## 5. 常见问题

- **vLLM 起不来 / OOM**：检查 `--tensor-parallel-size` 是否与 GPU 数量匹配；显存不足时降低 `--max-model-len`，或改为 `--dtype fp8`（需 FP8 卡）。
- **backend 连不上 vLLM**：确认 vllm 容器 `healthy`（`docker compose ps`），`VLLM_API_BASE` 在容器内应使用 `http://vllm:8000`。
- **Langfuse 空白页**：确认 `DATABASE_URL` 指向 postgres 且已 healthy；首次启动会执行数据库迁移，稍候片刻。
- **Grafana 无数据**：确认 datasource 为 `http://prometheus:9090`，且 backend / vllm 已暴露 `/metrics`。
- **GPU 未透传**：执行 `docker run --rm --gpus all nvidia/cuda:12.0-base nvidia-smi` 验证 NVIDIA Container Toolkit 安装。

## 6. 生产建议

起步采用单主机 Compose。生产环境建议：vLLM 独立多机部署、PostgreSQL 使用托管实例、引入 Kubernetes 编排、为 `.env` 中的密钥接入企业密钥管理（Vault）。
