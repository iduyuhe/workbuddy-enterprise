# model-gateway (:8001)

模型网关：统一 chat / completions / models，provider 抽象（vLLM / SGLang / Claude），
API Key 管理与 BYOK，模型路由与回退。

## 端点（API_CONTRACT §2）
- `POST /v1/chat`  (SSE, OpenAI 兼容) — 网关在此前已聚合 KB 上下文
- `POST /v1/completions` (非流式)
- `GET  /v1/models`
- `GET/PUT /admin/routes`
- `POST/GET /admin/keys`

provider 默认指向 env：
- `VLLM_API_BASE`   (默认 http://localhost:8080/v1)
- `DEEPSEEK_API_BASE`(默认 http://localhost:8081/v1)
- `CLAUDE_API_BASE` (默认空，可选)
- `ENABLE_MOCK=true`：当真实 provider 不可达时，回退到内置 mock 流式输出，便于本地无 GPU 跑通闭环。

## 运行
```bash
cd src/model-gateway
pip install -r requirements.txt
uvicorn app.main:app --port 8001 --reload
```
